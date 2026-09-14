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
     thresholds: default warn ≥ $250/day, page ≥ $750/day). --dry-run prints without sending.

Stdlib only; flare is shelled out (on PATH via ~/.local/bin). Key from
RUNPOD_API_KEY in env / ~/.env, else ~/.runpod/config.toml. RunPod's REST v2
403s python-urllib's default User-Agent, so a curl UA is sent.

Usage:
  python3 digest.py --dry-run
  python3 digest.py --dry-run --as-of 2026-08-01   # replay a past day
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

SMALL_POD = 5.0   # $/day below which a vanished pod is "short-lived eval pod" noise, not an owner question


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


def owner(labels: list[str]) -> str | None:
    """Primary thread for a pod, or None when the only evidence is an undeclared session."""
    for lab in labels:
        if not lab.startswith("undeclared"):
            return lab
    return None


def flat_days(series: list[float]) -> int:
    """How many consecutive earlier days billed within 5% of the last one (leak signature)."""
    if not series:
        return 0
    last, n = series[-1], 0
    for v in reversed(series[:-1]):
        if last > 1 and abs(v - last) <= 0.05 * last:
            n += 1
        else:
            break
    return n


def render(now, pods, totals, per_pod, attr, acct, warn, page) -> tuple[str, str]:
    """totals: {date: all-scope record}, per_pod: {date: {pod_id: $}} for the trailing window."""
    yd = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    days = sorted(d for d in per_pod if d < now.strftime("%Y-%m-%d"))
    y_total = (totals.get(yd) or {}).get("totalAmount", 0.0)
    y_pod = per_pod.get(yd, {})
    running = [p for p in pods if p.get("status") == "RUNNING"]
    gpu_running = [p for p in running if (p.get("cost") or 0) >= 0.5]
    burn = sum(p.get("cost") or 0 for p in running)
    is_infra = lambda pid: (attr.get(pid) or [""])[0] == "infra (allowlist)"  # noqa: E731

    # ── yesterday, grouped by owner
    groups: dict[str, dict] = {}
    for pid, amt in y_pod.items():
        labs = attr.get(pid) or []
        own = owner(labs)
        alive = pid in {p["id"] for p in pods}
        if own is None and not alive and amt < SMALL_POD:
            own = "short-lived eval pods"
        key = own or "⚠ unattributed"
        g = groups.setdefault(key, {"amt": 0.0, "pods": [], "hints": set()})
        g["amt"] += amt
        g["pods"].append(pid)
        if own is None:
            g["hints"].update(l for l in labs if l.startswith("undeclared"))
    orphans = [pid for pid in groups.get("⚠ unattributed", {}).get("pods", [])]
    gpu_orphans = [p for p in gpu_running if owner(attr.get(p["id"]) or []) is None]

    # ── headline
    date = (now - timedelta(days=1)).strftime("%a %-d %b")
    series = [(totals.get(d) or {}).get("totalAmount", 0.0) for d in days]
    fl = flat_days(series)
    head = f"RunPod, {date}: ${y_total:,.0f} spent"
    head += f", same as the last {fl} days" if fl >= 3 else ""
    head += "."
    flat_orphans = [pid for pid in orphans
                    if flat_days([per_pod.get(d, {}).get(pid, 0.0) for d in days]) >= 2]
    loud = sorted({o["id"] for o in gpu_orphans} | set(flat_orphans))
    if loud:
        head += f" ⚠ {len(loud)} pod{'s' if len(loud) > 1 else ''} with no owner."
    elif gpu_running:
        head += f" {len(gpu_running)} GPU pod{'s' if len(gpu_running) > 1 else ''} running, ${burn:,.0f}/h."
    else:
        head += " Nothing burning today."
    lines = [head, ""]

    # ── yesterday breakdown
    if y_pod:
        lines.append(f"Yesterday's ${y_total:,.0f} went to:")
        pod_by_id = {p["id"]: p for p in pods}
        for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["amt"]):
            n = len(g["pods"])
            if key == "infra (allowlist)":
                names = ", ".join(pod_by_id[pid].get("name", pid) for pid in g["pods"] if pid in pod_by_id)
                lines.append(f"  • infra — ${g['amt']:,.0f} ({names})")
            elif key == "short-lived eval pods":
                lines.append(f"  • short-lived eval pods — ${g['amt']:,.0f}, {n} pods")
            elif key == "⚠ unattributed":
                for pid in g["pods"]:
                    p = pod_by_id.get(pid)
                    shape = f"{gpu_label(p)}, up {age(p.get('createdAt'), now)}" if p else "gone"
                    hist = [per_pod.get(d, {}).get(pid, 0.0) for d in days]
                    f = flat_days(hist)
                    flat = f", flat for {f + 1} days" if f >= 2 else ""
                    hint = f" (seen in: {', '.join(sorted(g['hints']))})" if g["hints"] else ""
                    lines.append(f"  • ⚠ unattributed — ${y_pod[pid]:,.0f}, {pid} ({shape}{flat}){hint}")
            else:
                shapes = sorted({gpu_label(pod_by_id[pid]) for pid in g["pods"] if pid in pod_by_id})
                what = f"{n} pod{'s' if n > 1 else ''}" + (f", {'/'.join(shapes)}" if shapes else "")
                alive = [pid for pid in g["pods"] if pid in pod_by_id and pod_by_id[pid].get("status") == "RUNNING"]
                state = "" if alive or key == "infra (allowlist)" else ", torn down"
                lines.append(f"  • {key} — ${g['amt']:,.0f}, {what}{state}")
        lines.append("")

    # ── running now
    if gpu_running:
        lines.append(f"Running now (${burn:,.0f}/h):")
        for p in sorted(gpu_running, key=lambda p: -(p.get("cost") or 0)):
            own = owner(attr.get(p["id"]) or [])
            up = age(p.get("createdAt"), now)
            mark = " ⚠ no owner" if own is None else ""
            lines.append(f"  • {own or '⚠ unattributed'} — {p['id']} {gpu_label(p)} ${p.get('cost') or 0:,.2f}/h, up {up}{mark}")
        infra = [p for p in running if is_infra(p["id"])]
        if infra:
            lines.append(f"  • infra — {len(infra)} CPU pods ${sum(p.get('cost') or 0 for p in infra):,.2f}/h")
    else:
        infra = [p for p in running if is_infra(p["id"])]
        lines.append(f"Running now: only the {len(infra)} infra CPU pods (${burn:,.2f}/h)." if infra and len(infra) == len(running)
                     else f"Running now: {len(running)} pods, ${burn:,.2f}/h, no GPU.")
    stopped = [p for p in pods if p.get("status") != "RUNNING"]
    if stopped:
        lines.append(f"Stopped but still billing disk: {', '.join(p.get('name') or p['id'] for p in stopped)}.")

    # ── balance / runway / kill line
    bal = acct.get("clientBalance")
    if bal is not None:
        tail = f"Balance ${bal:,.0f}."
        if burn >= 1:
            tail += f" At this burn, {bal / (burn * 24):.0f} days."
        lines.append(tail)
    kill = sorted({p["id"] for p in gpu_orphans} | {pid for pid in orphans if pid in {p["id"] for p in running}})
    if kill:
        lines.append(f"Kill: runpodctl remove pod {' '.join(kill)}")

    sev = "info"
    if loud:
        sev = "warn"
    if y_total >= page:
        sev = "page"
    elif y_total >= warn and sev == "info":
        sev = "warn"
    return "\n".join(lines), sev


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--allowlist", type=Path,
                    default=Path(__file__).resolve().parent / "allowlist.json",
                    help="pod-audit style allowlist of intended long-lived pods")
    ap.add_argument("--out", type=Path, help="append one JSONL ledger record here")
    ap.add_argument("--warn-daily", type=float, default=250.0, help="sev=warn above this $/day")
    ap.add_argument("--page-daily", type=float, default=750.0, help="sev=page above this $/day")
    ap.add_argument("--dry-run", action="store_true", help="print, don't flare")
    ap.add_argument("--as-of", help="replay: render as if run at 00:05 UTC on this YYYY-MM-DD (pod list is still live)")
    a = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    if a.as_of:
        now = datetime.strptime(a.as_of, "%Y-%m-%d").replace(hour=0, minute=5, tzinfo=timezone.utc)
    key = api_key()
    pods = paged("/pods", key, "pods")
    day0 = (now - timedelta(days=10)).strftime("%Y-%m-%dT00:00:00Z")
    day2 = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    win = dict(bucketSize="day", startTime=day0, endTime=day2)
    totals = {r["startTime"][:10]: r for r in paged("/billing", key, "records", scope="all", **win)}
    per_pod: dict[str, dict[str, float]] = {}
    for r in paged("/billing/pods", key, "records", **win):
        per_pod.setdefault(r["startTime"][:10], {})[r["podId"]] = r["totalAmount"]
    yd, td = (now - timedelta(days=1)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    y_pod = per_pod.get(yd, {})

    allow = json.loads(a.allowlist.read_text()) if a.allowlist.exists() else {}
    names = {p["id"]: p.get("name") or "" for p in pods}
    for pid in y_pod:
        names.setdefault(pid, "")
    attr = attribute(names, allow, os.environ.get("CLAUDE_CODE_SESSION_ID"))
    msg, sev = render(now, pods, totals, per_pod, attr, account(key), a.warn_daily, a.page_daily)
    b_all = totals

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
