#!/usr/bin/env python3
"""thesis-keeper: keep exactly one live [phd-thesis] task in the concierge pool.

The standing worker assignment for goals/phd-thesis.md (Daniel, 2026-08-23:
1 active worker, 24/7; automation=dispatch). Half-hourly cron. Cheap guard
first: if any non-terminal pool task is titled with the [phd-thesis] prefix,
exit silently — the worker slot is occupied. Only when the slot is free does
it spend a model call: a headless dispatcher session (claude -p) reads the
goal file and specs + submits the next task per ops/thesis-keeper.md.

Also watches the daemon: tasks queue forever if the `concierge` tmux session
is down, so that transition gets a warn flare (edge-triggered via marker file).
"""

import os
import subprocess
import sys
from pathlib import Path

HOME = Path(os.environ.get("CONCIERGE_HOME", str(Path.home() / "concierge-home")))
JARVIS = Path.home() / "jarvis"
PROMPT_DOC = "jarvis-os/ops/thesis-keeper.md"
TITLE_PREFIX = "[phd-thesis]"
DAEMON_DOWN_MARKER = Path.home() / ".claude" / "logs" / ".thesis-keeper-daemon-down"
DISPATCH_TIMEOUT_S = 45 * 60


def flare(msg: str, sev: str = "info") -> None:
    subprocess.run(["flare", msg, "--sev", sev], check=False)


def daemon_alive() -> bool:
    return (
        subprocess.run(
            ["tmux", "has-session", "-t", "concierge"], capture_output=True
        ).returncode
        == 0
    )


def live_thesis_tasks() -> list:
    sys.path.insert(0, str(JARVIS / "jarvis-tools" / "packages" / "concierge"))
    from concierge.api import Pool
    from concierge.records import TERMINAL

    pool = Pool(str(HOME))
    return [
        t
        for t in pool.tasks()
        if t["status"] not in TERMINAL
        and (t.get("title") or "").startswith(TITLE_PREFIX)
    ]


def main() -> int:
    if not daemon_alive():
        # Edge-triggered: one warn per outage, not one per tick.
        if not DAEMON_DOWN_MARKER.exists():
            DAEMON_DOWN_MARKER.touch()
            flare(
                "thesis-keeper: concierge tmux session is DOWN — thesis worker "
                "pool stalled until the daemon is restarted",
                sev="warn",
            )
        print("daemon down; skipping")
        return 0
    DAEMON_DOWN_MARKER.unlink(missing_ok=True)

    live = live_thesis_tasks()
    if live:
        print(f"slot occupied: {live[0]['id']} [{live[0]['status']}] {live[0].get('title')}")
        return 0

    print("slot free — launching dispatcher")
    prompt = (
        f"You are the thesis-keeper dispatcher. Follow {PROMPT_DOC} exactly: "
        f"pick the next unit of thesis work, spec it fully, and submit exactly "
        f"one concierge task titled with the {TITLE_PREFIX} prefix. If the doc "
        f"and reality conflict, trust reality and note the discrepancy in your "
        f"thread note."
    )
    proc = subprocess.run(
        ["claude", "-p", prompt, "--dangerously-skip-permissions"],
        cwd=str(JARVIS),
        timeout=DISPATCH_TIMEOUT_S,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout[-4000:])
    sys.stderr.write(proc.stderr[-2000:])

    # Trust-but-verify: the dispatcher's one job is a submission; if the slot
    # is still empty, say so rather than silently retrying forever.
    if not live_thesis_tasks():
        flare(
            "thesis-keeper: dispatcher ran but no [phd-thesis] task appeared "
            "in the pool — check ~/.claude/logs/thesis-keeper.log",
            sev="warn",
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
