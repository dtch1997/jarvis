#!/usr/bin/env python3
"""pod-digest — one daily RunPod message: active pods, spend, and which thread owns each pod.

Born from the 2026-09-14 spend audit (experiments/runpod-spend-audit): five
leak / crash-loop incidents ≈ $5k, none noticed for days because nothing
reported spend daily and pods carried no thread attribution. This tick sends
one flare per day that answers "what is running, what did it cost, whose is it".

Per tick:
  1. Active pods via RunPod REST v2 (`/pods`).
  2. Spend: yesterday (full UTC day) + today-so-far, account-level and per pod
     (`/billing`, `/billing/pods`, bucketSize=day) plus balance/burn via GraphQL.
  3. Attribution of every pod id seen (running, or billed in the window) to
     thread slug(s), cheapest evidence first:
       - allowlist.json (pod-audit's list of intended long-lived pods) → infra
       - pod NAME contains a thread slug (memory stub / thread-note slug)
       - pod ID appears in ~/.threads/notes/<slug>/*.md       → slug
       - pod ID appears in ~/jarvis-memory/<slug>.md            → slug
       - pod ID appears in ~/concierge-home/{tasks,specs,logs}  → concierge task
       - pod ID appears in a ~/.claude/projects transcript      → the session's
         declared slug (~/.threads/sessions/<id>.json), else "undeclared session"
     Anything left is UNATTRIBUTED and printed loudly.
  4. Renders one message, appends a JSONL ledger record (--out), and sends it
     with `flare` (--sev info; warn/page when spend or an orphan crosses the
     thresholds). --dry-run prints without sending.

Stdlib only; flare is shelled out (on PATH via ~/.local/bin). Key from
RUNPOD_API_KEY in env / ~/.env, else ~/.runpod/config.toml. RunPod's REST v2
403s python-urllib's default User-Agent, so a curl UA is sent.

Usage:
  python3 digest.py --dry-run
  python3 digest.py --out ~/jarvis-data/pod-digest/ledger.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.runpod.io/v2"
GQL = "https://api.runpod.io/graphql"
HOME = Path.home()
MEMORY = HOME / "jarvis-memory"
NOTES = HOME / ".threads" / "notes"
SESSIONS = HOME / ".threads" / "sessions"
CANDIDATES = HOME / ".threads" / "candidates"
PROJECTS = HOME / ".claude" / "projects"
CONCIERGE = HOME / "concierge-home"


# ── RunPod ────────────────────────────────────────────────────────────────────

def api_key() -> str:
    k = os.environ.get("RUNPOD_API_KEY")
    if not k and (HOME / ".env").exists():
        for line in (HOME / ".env").read_text().splitlines():
            if line.startswith("RUNPOD_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k and (HOME / ".runpod" / "config.toml").exists():
        m = re.search(r"apikey\s*=\s*'([^']+)'", (HOME / ".runpod" / "config.toml").read_text())
        k = m.group(1) if m else None
    if not k:
        sys.exit("no RunPod API key (RUNPOD_API_KEY / ~/.env / ~/.runpod/config.toml)")
    return k


def _req(url: str, key: str, data: bytes | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {key}", "User-Agent": "curl/8.5.0",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def paged(path: str, key: str, item_key: str, **params) -> list[dict]:
    cur, out = None, []
    while True:
        q = "&".join(f"{a}={b}" for a, b in {**params, "limit": 100, "cursor": cur}.items() if b is not None)
        d = _req(f"{API}{path}?{q}", key)
        out += d.get(item_key, [])
        cur = (d.get("pagination") or {}).get("nextCursor")
        if not cur:
            return out


def account(key: str) -> dict:
    try:
        q = {"query": "{ myself { clientBalance currentSpendPerHr } }"}
        return _req(GQL, key, json.dumps(q).encode()).get("data", {}).get("myself", {}) or {}
    except Exception:  # noqa: BLE001 — balance is decoration, never fail the digest on it
        return {}


# ── attribution ───────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def known_slugs() -> set[str]:
    slugs = {p.stem for p in MEMORY.glob("*.md") if p.stem != "MEMORY"}
    for d in (NOTES, CANDIDATES):
        if d.exists():
            slugs |= {p.stem if p.is_file() else p.name for p in d.iterdir()}
    return {s for s in slugs if len(s) >= 4}


def grep_ids(ids: list[str], roots: list[Path]) -> dict[str, set[Path]]:
    """pod id -> files mentioning it (one grep -F pass over all roots)."""
    hits: dict[str, set[Path]] = {i: set() for i in ids}
    roots = [r for r in roots if r.exists()]
    if not ids or not roots:
        return hits
    pat = "\n".join(ids) + "\n"
    p = subprocess.run(["grep", "-rIoF", "-f", "-", *map(str, roots)],
                       input=pat, capture_output=True, text=True, timeout=600)
    for line in p.stdout.splitlines():
        f, _, pid = line.rpartition(":")
        if pid in hits:
            hits[pid].add(Path(f))
    return hits


def session_slug(session_id: str) -> str:
    f = SESSIONS / f"{session_id}.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            return d.get("slug") or f"undeclared session {session_id[:8]}"
        except json.JSONDecodeError:
            pass
    return f"undeclared session {session_id[:8]}"


def attribute(pods: dict[str, str], allow: dict, self_session: str | None) -> dict[str, list[str]]:
    """{pod_id: [attribution labels]} — pods = {id: name}.

    Labels are ordered by evidence quality: allowlist, slug in the pod name,
    thread note, memory stub, concierge task, declared session, and finally
    (only when nothing else matched) one undeclared session.
    """
    slugs = sorted(known_slugs(), key=len, reverse=True)
    tiers: dict[str, dict[int, list[str]]] = {pid: {} for pid in pods}

    def add(pid: str, tier: int, lab: str) -> None:
        t = tiers[pid].setdefault(tier, [])
        if lab not in t:
            t.append(lab)

    for pid, name in pods.items():
        if name in allow:
            add(pid, 0, "infra (allowlist)")
            continue  # infra pods show up in every `pod list` — transcript hits are noise
        n = _norm(name)
        for s in slugs:
            if s in n:
                add(pid, 1, s)
                break
    ids = [pid for pid in pods if 0 not in tiers[pid]]
    hits = grep_ids(ids, [NOTES, MEMORY, CONCIERGE / "tasks", CONCIERGE / "specs", PROJECTS])
    for pid, files in hits.items():
        for f in sorted(files):
            parts = f.parts
            if NOTES in f.parents:
                add(pid, 2, parts[parts.index("notes") + 1])
            elif MEMORY in f.parents:
                if f.stem != "MEMORY":
                    add(pid, 3, f.stem)
            elif CONCIERGE in f.parents:
                add(pid, 4, f"concierge {f.stem}")
            elif PROJECTS in f.parents:
                # <proj>/<session>.jsonl or <proj>/<session>/subagents/agent-*.jsonl
                rel = f.relative_to(PROJECTS).parts
                sid = rel[1].split(".")[0] if len(rel) >= 2 else ""
                if not sid or (self_session and sid.startswith(self_session)):
                    continue
                lab = session_slug(sid)
                add(pid, 6 if lab.startswith("undeclared") else 5, lab)
    out: dict[str, list[str]] = {}
    for pid, t in tiers.items():
        labels: list[str] = []
        for tier in sorted(t):
            if tier < 6:
                labels += [lab for lab in t[tier] if lab not in labels]
        if not labels and 6 in t:
            labels = t[6][:1]
        out[pid] = labels
    return out


# ── render ────────────────────────────────────────────────────────────────────

def age(iso: str | None, now: datetime) -> str:
    if not iso:
        return "?"
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    h = (now - t).total_seconds() / 3600
    return f"{h/24:.0f}d" if h >= 48 else f"{h:.0f}h"


def gpu_label(p: dict) -> str:
    g = p.get("gpu") or {}
    if isinstance(g, dict) and (g.get("id") or g.get("displayName")):
        n = g.get("count") or p.get("gpuCount") or 1
        return f"{n}×{g.get('displayName') or g.get('id')}"
    m = p.get("machine") or {}
    if isinstance(m, dict) and m.get("gpuDisplayName"):
        return f"{p.get('gpuCount', 1)}×{m['gpuDisplayName']}"
    return "CPU"


def render(now, pods, y_all, t_all, y_pod, t_pod, attr, acct, warn, page) -> tuple[str, str]:
    y = y_all.get("totalAmount", 0.0) if y_all else 0.0
    t = t_all.get("totalAmount", 0.0) if t_all else 0.0
    yd = (now - timedelta(days=1)).date()
    sev = "info"
    head = [f"pod-digest {now.date()} · yesterday ({yd}) ${y:,.2f}"
            + (f" (gpu {y_all.get('podGpuAmount', 0):,.0f} · cpu {y_all.get('podCpuAmount', 0):,.2f}"
               f" · cluster {y_all.get('clusterGpuAmount', 0) + y_all.get('clusterNetworkingAmount', 0):,.0f}"
               f" · storage {y_all.get('podDiskAmount', 0) + y_all.get('storageStandardAmount', 0):,.2f})" if y_all else "")
            + f" · today so far ${t:,.2f}"]
    if acct:
        head[0] += f" · balance ${acct.get('clientBalance', 0):,.0f} · burn ${acct.get('currentSpendPerHr', 0):.2f}/h"
    lines = list(head)
    running = [p for p in pods if p.get("status") == "RUNNING"]
    stopped = [p for p in pods if p.get("status") != "RUNNING"]
    lines.append(f"ACTIVE ({len(running)} running, {len(stopped)} stopped):")
    unattributed = []
    for p in sorted(pods, key=lambda p: -(p.get("cost") or 0)):
        labs = attr.get(p["id"]) or []
        if not labs:
            unattributed.append(p)
        lab = " / ".join(labs[:3]) if labs else "⚠ UNATTRIBUTED"
        lines.append(f"• {p.get('name') or '(unnamed)'} `{p['id']}` {gpu_label(p)} ${p.get('cost') or 0:.2f}/h"
                     f" {p.get('status', '?').lower()} up {age(p.get('createdAt'), now)}"
                     f" · y ${y_pod.get(p['id'], 0):.2f} · today ${t_pod.get(p['id'], 0):.2f} · {lab}")
    gone = [(pid, amt) for pid, amt in y_pod.items() if pid not in {p["id"] for p in pods} and amt >= 0.5]
    if gone:
        lines.append(f"BILLED YESTERDAY, NOW GONE ({len(gone)}):")
        for pid, amt in sorted(gone, key=lambda x: -x[1])[:15]:
            labs = attr.get(pid) or []
            lines.append(f"• `{pid}` ${amt:.2f} · {' / '.join(labs[:3]) if labs else '⚠ UNATTRIBUTED'}")
        if len(gone) > 15:
            lines.append(f"  … +{len(gone) - 15} more (${sum(a for _, a in gone[15:]):.2f})")
    # severity
    for p in running:
        labs = attr.get(p["id"]) or []
        if (p.get("cost") or 0) >= 0.5 and (not labs or all(l.startswith("undeclared") for l in labs)):
            sev = "warn"
            lines.append(f"⚠ GPU pod `{p['id']}` ({p.get('name')}) has no thread attribution — leak candidate")
    if y >= page:
        sev = "page"
    elif y >= warn and sev == "info":
        sev = "warn"
    return "\n".join(lines), sev


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--allowlist", type=Path,
                    default=Path(__file__).resolve().parent / "allowlist.json",
                    help="pod-audit style allowlist of intended long-lived pods")
    ap.add_argument("--out", type=Path, help="append one JSONL ledger record here")
    ap.add_argument("--warn-daily", type=float, default=150.0, help="sev=warn above this $/day")
    ap.add_argument("--page-daily", type=float, default=400.0, help="sev=page above this $/day")
    ap.add_argument("--dry-run", action="store_true", help="print, don't flare")
    a = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    key = api_key()
    pods = paged("/pods", key, "pods")
    day0 = (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    day2 = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    win = dict(bucketSize="day", startTime=day0, endTime=day2)
    b_all = {r["startTime"][:10]: r for r in paged("/billing", key, "records", scope="all", **win)}
    b_pod = paged("/billing/pods", key, "records", **win)
    yd, td = (now - timedelta(days=1)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    y_pod = {r["podId"]: r["totalAmount"] for r in b_pod if r["startTime"][:10] == yd}
    t_pod = {r["podId"]: r["totalAmount"] for r in b_pod if r["startTime"][:10] == td}

    allow = json.loads(a.allowlist.read_text()) if a.allowlist.exists() else {}
    names = {p["id"]: p.get("name") or "" for p in pods}
    for pid in set(y_pod) | set(t_pod):
        names.setdefault(pid, "")
    attr = attribute(names, allow, os.environ.get("CLAUDE_CODE_SESSION_ID"))
    msg, sev = render(now, pods, b_all.get(yd), b_all.get(td), y_pod, t_pod, attr,
                      account(key), a.warn_daily, a.page_daily)

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("a") as f:
            f.write(json.dumps({"ts": now.isoformat(), "sev": sev,
                                "yesterday": (b_all.get(yd) or {}).get("totalAmount", 0.0),
                                "today": (b_all.get(td) or {}).get("totalAmount", 0.0),
                                "pods": [{"id": p["id"], "name": p.get("name"), "status": p.get("status"),
                                          "cost_per_hr": p.get("cost"), "threads": attr.get(p["id"], [])}
                                         for p in pods],
                                "billed_yesterday": {pid: {"amount": amt, "threads": attr.get(pid, [])}
                                                     for pid, amt in y_pod.items()}}) + "\n")
    print(f"[{sev}]\n{msg}")
    if not a.dry_run:
        subprocess.run(["flare", "--sev", sev, "--source", "pod-digest", msg], check=False, timeout=60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
