"""Actuators — land a triaged thought on an existing spine.

Every actuator is reversible (draft-and-veto): a threads note, a Todoist move,
a dated goal bullet, a flare. The top rung (dispatching a concierge task) is
propose-only at MVP — it never runs here, only surfaces in the digest. Each
external effect is a seam so tests never touch the real spines.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config


# --------------------------------------------------------------------------- #
# threads note — land on an ongoing thread (seeds a candidate thread if new)
# --------------------------------------------------------------------------- #
def default_note_runner(slug: str, body: str, *, status: str | None = None) -> str:
    argv = ["threads", "note", slug, "-"]
    if status:
        argv += ["--status", status]
    proc = subprocess.run(argv, input=body, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "threads note failed").strip())
    return proc.stdout.strip()


def land_note(slug: str, thought: dict, *, note_runner=default_note_runner,
              status: str = "parked") -> str:
    title = (thought.get("triage") or {}).get("title") or "captured thought"
    body = (
        f"# {title}\n\n"
        f"{thought.get('raw', '').strip()}\n\n"
        f"---\n_via mailroom · source: {thought.get('source')} · "
        f"{thought.get('permalink', '')}_\n"
    )
    note_runner(slug, body, status=status)
    return slug


# --------------------------------------------------------------------------- #
# goal-signal — dated bullet in the goal file's Parked follow-ups section
# --------------------------------------------------------------------------- #
_PARKED_HEADING = "## Parked follow-ups"


def append_goal_bullet(goal_slug: str, text: str, *, now: datetime | None = None,
                       goals_dir: Path | None = None) -> Path | None:
    now = now or datetime.now(timezone.utc)
    d = goals_dir or config.goals_dir()
    path = d / f"{goal_slug}.md"
    if not path.exists():
        return None
    stamp = now.strftime("%Y-%m-%d")
    bullet = f"- ({stamp}, via mailroom) {text.strip()}\n"
    content = path.read_text()
    if _PARKED_HEADING in content:
        head, sep, rest = content.partition(_PARKED_HEADING + "\n")
        # insert right after the heading line
        path.write_text(head + sep + bullet + rest)
    else:
        sep = "" if content.endswith("\n") else "\n"
        path.write_text(content + f"{sep}\n{_PARKED_HEADING}\n\n{bullet}")
    return path


# --------------------------------------------------------------------------- #
# urgent / blocked — flare
# --------------------------------------------------------------------------- #
def send_flare(text: str, *, sev: str = "warn") -> bool:
    try:
        import flare
        flare.send(text, sev=sev, source="mailroom")
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# paper — arxivist fetch when an arXiv id is present (best-effort seam)
# --------------------------------------------------------------------------- #
def default_arxiv_runner(arxiv_id: str) -> bool:
    try:
        proc = subprocess.run(["arxivist", "fetch", arxiv_id],
                              capture_output=True, text=True, timeout=60)
        return proc.returncode == 0
    except Exception:
        return False
