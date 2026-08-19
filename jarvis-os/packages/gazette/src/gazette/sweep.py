"""The sweep (hourly since the 2026-08-19 rework): decide every open PR,
merge what the lanes allow — auto merges on green, requires-approval never —
record everything to the spool (``~/.gazette/log.jsonl``) for the notes."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from . import gh
from .config import Config, spool_dir
from .lanes import PR, Decision, decide


def log_path():
    return spool_dir() / "log.jsonl"


def _record(entry: dict) -> None:
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass


def run(cfg: Config, now: datetime | None = None, dry_run: bool = False) -> dict:
    """Returns a report: {merged, waiting, skipped, errors, unswept, warnings}."""
    now = now or datetime.now(timezone.utc)
    report: dict = {
        "merged": [], "waiting": [], "skipped": [], "errors": [], "unswept": [],
        "warnings": [],
    }
    for repo in cfg.github_repos:
        prs, warnings, _failed = gh.list_open_prs(repo)
        report["warnings"].extend(warnings)
        for pr in prs:
            decision = decide(pr, cfg, now)
            row = {
                "ts": now.isoformat(),
                "repo": repo,
                "number": pr.number,
                "ref": pr.ref,
                "title": pr.title,
                "url": pr.url,
                "lane": decision.lane.value,
                "action": decision.action,
                "reason": decision.reason,
                "anomalies": decision.anomalies,
                "dry_run": dry_run,
            }
            if decision.action == "merge" and not dry_run:
                err = gh.merge_pr(pr)
                if err:
                    row["action"] = "error"
                    row["reason"] = err
                    report["errors"].append(row)
                else:
                    report["merged"].append(row)
            elif decision.action == "merge":
                row["action"] = "would-merge"
                report["merged"].append(row)
            elif decision.action == "wait":
                report["waiting"].append(row)
            else:
                report["skipped"].append(row)
            _record(row)
    # Coverage, not policy: lane-labelled PRs in repos this config does not
    # sweep get no decision above — they are simply never enumerated. Surface
    # them (and spool them) so a repo that opted into lanes without being
    # configured is loud, the way a collector failure is (issue #21's lesson,
    # one level up).
    strays, stray_warnings = gh.unswept_lane_prs(cfg)
    report["warnings"].extend(stray_warnings)
    for stray in strays:
        row = {
            "ts": now.isoformat(),
            "repo": stray["repo"],
            "number": stray["number"],
            "ref": f"{stray['repo'].split('/')[-1]}#{stray['number']}",
            "title": stray["title"],
            "url": stray["url"],
            "lane": stray["label"].split(":", 1)[-1],
            "action": "unswept",
            "reason": f"carries {stray['label']} but {stray['repo']} is not in github_repos",
            "anomalies": ["repo not swept — no sweep will ever decide this PR"],
            "dry_run": dry_run,
        }
        report["unswept"].append(row)
        _record(row)
    report["warnings"].extend(gh.coverage_gap_messages(strays))
    return report


def format_report(report: dict) -> str:
    lines = []
    for key in ("merged", "waiting", "skipped", "errors", "unswept"):
        for row in report[key]:
            lines.append(f"[{row['action']}] {row['ref']} ({row['lane']}) — {row['reason']}")
    for w in report["warnings"]:
        lines.append(f"[warn] {w}")
    return "\n".join(lines) if lines else "nothing to do"
