#!/usr/bin/env python3
"""RunPod pod audit — one tick per invocation (cron-driven, weekly).

Motivation (2026-08-13): two bellhop-launched GPU pods (an H200 "graft-smoke"
and a 4090 "flash-wheel" build) outlived their TTL teardown and idled for ~3
weeks at ~$5.33/hr combined — roughly $4,900 burned before a manual pod
listing caught them. This audit is the backstop for the next leak.

What it does, per tick:
  1. Lists all pods via the RunPod REST API (key read from
     ~/.runpod/config.toml — same credential runpodctl uses).
  2. Compares against an allowlist of intended long-lived pods
     (allowlist.json next to this script, or --allowlist).
  3. Flags:
       - RUNNING GPU pod not on the allowlist, older than --gpu-max-hours
         (leaked compute — the expensive case)
       - RUNNING CPU pod not on the allowlist, older than --cpu-max-hours
       - EXITED pod not on the allowlist (stopped pods still bill
         container-disk storage)
       - allowlisted pod whose costPerHr exceeds its max_cost_per_hr
         (name reused on unexpectedly expensive hardware)
  4. Appends one JSONL audit record to --out.
  5. If anything is flagged (and --github-repo is set, not --dry-run):
     opens a GitHub issue titled "[pod-audit] ..." — or comments on the
     open one — with a table of offenders, burn estimates, and the
     runpodctl commands to kill them. Propose-only: this script never
     deletes a pod itself.

Zero deps (stdlib urllib) so cron needs no venv; escalation shells out to
`gh`, which is already authenticated on this box.

Usage:
  python3 audit.py --dry-run                # print findings, no issue
  python3 audit.py --out audit.jsonl --github-repo ArcadiaImpact/jarvis
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REST_URL = "https://rest.runpod.io/v1/pods"  # v2 exists; v1 verified working with this key


def api_key() -> str:
    text = (Path.home() / ".runpod" / "config.toml").read_text()
    m = re.search(r"apikey\s*=\s*'([^']+)'", text)
    if not m:
        sys.exit("no apikey in ~/.runpod/config.toml")
    return m.group(1)


def list_pods() -> list[dict]:
    req = urllib.request.Request(REST_URL, headers={"Authorization": f"Bearer {api_key()}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse_runpod_ts(ts: str) -> datetime | None:
    # e.g. "2026-07-24 03:46:26.085 +0000 UTC" (fraction optional)
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)?", ts or "")
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def audit(pods: list[dict], allowlist: dict, gpu_max_h: float, cpu_max_h: float) -> list[dict]:
    now = datetime.now(timezone.utc)
    flags = []
    for p in pods:
        name, status = p.get("name", ""), p.get("desiredStatus", "")
        gpu = p.get("gpuCount", 0) or 0
        cost = p.get("costPerHr", 0) or 0
        started = parse_runpod_ts(p.get("lastStartedAt", ""))
        age_h = (now - started).total_seconds() / 3600 if started else None
        allowed = allowlist.get(name)

        reason = None
        if allowed is not None:
            max_cost = allowed.get("max_cost_per_hr", 0.10)
            if cost > max_cost:
                reason = f"allowlisted name but costPerHr ${cost:.2f} > expected ${max_cost:.2f}"
        elif status == "RUNNING":
            if gpu > 0 and age_h is not None and age_h > gpu_max_h:
                reason = f"GPU pod running {age_h:.0f}h (limit {gpu_max_h:.0f}h), not allowlisted"
            elif gpu == 0 and age_h is not None and age_h > cpu_max_h:
                reason = f"CPU pod running {age_h:.0f}h (limit {cpu_max_h:.0f}h), not allowlisted"
        elif status == "EXITED":
            reason = f"stopped pod still billing {p.get('containerDiskInGb', 0)}GB container disk"

        if reason:
            flags.append({
                "id": p.get("id"), "name": name, "status": status,
                "gpuCount": gpu, "costPerHr": cost, "age_hours": round(age_h, 1) if age_h else None,
                "est_burn_usd": round(cost * age_h, 2) if (age_h and status == "RUNNING") else None,
                "reason": reason,
            })
    return flags


def issue_body(flags: list[dict]) -> str:
    lines = [
        "Weekly RunPod pod audit found pods that look leaked. "
        "**Propose-only** — nothing has been deleted.",
        "",
        "| pod | id | status | GPUs | $/hr | age (h) | est. burn | reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in flags:
        burn = f"${f['est_burn_usd']:,.0f}" if f["est_burn_usd"] else "—"
        lines.append(
            f"| {f['name']} | `{f['id']}` | {f['status']} | {f['gpuCount']} "
            f"| {f['costPerHr']} | {f['age_hours'] or '—'} | {burn} | {f['reason']} |"
        )
    lines += ["", "To terminate after checking nothing is running on them:", "```"]
    lines += [f"runpodctl pod delete {f['id']}  # {f['name']}" for f in flags]
    lines += ["```", "", "_Source: `ops/pod-audit/audit.py` (weekly cron)._"]
    return "\n".join(lines)


def escalate(repo: str, flags: list[dict]) -> None:
    title = "[pod-audit] leaked RunPod pods detected"
    found = subprocess.run(
        ["gh", "issue", "list", "-R", repo, "--state", "open",
         "--search", "[pod-audit] in:title", "--json", "number"],
        capture_output=True, text=True, check=True)
    open_issues = json.loads(found.stdout or "[]")
    body = issue_body(flags)
    if open_issues:
        n = str(open_issues[0]["number"])
        subprocess.run(["gh", "issue", "comment", n, "-R", repo, "--body", body], check=True)
        print(f"commented on existing issue #{n}")
    else:
        subprocess.run(["gh", "issue", "create", "-R", repo, "--title", title, "--body", body], check=True)
        print("opened new issue")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", type=Path, default=Path(__file__).parent / "allowlist.json")
    ap.add_argument("--out", type=Path, help="JSONL file to append the audit record to")
    ap.add_argument("--github-repo", help="owner/repo to open the escalation issue on")
    ap.add_argument("--gpu-max-hours", type=float, default=12)
    ap.add_argument("--cpu-max-hours", type=float, default=72)
    ap.add_argument("--dry-run", action="store_true", help="print findings, skip issue + jsonl")
    args = ap.parse_args()

    allowlist = json.loads(args.allowlist.read_text())
    pods = list_pods()
    flags = audit(pods, allowlist, args.gpu_max_hours, args.cpu_max_hours)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_pods": len(pods), "n_flagged": len(flags),
        "total_cost_per_hr": round(sum(p.get("costPerHr", 0) or 0 for p in pods), 3),
        "flags": flags,
    }
    print(json.dumps(record, indent=2))

    if args.dry_run:
        return
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("a") as f:
            f.write(json.dumps(record) + "\n")
    if flags and args.github_repo:
        escalate(args.github_repo, flags)


if __name__ == "__main__":
    main()
