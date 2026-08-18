"""Read/write the ``~/.mailroom`` spool: thought records + state (cursors).

A thought record (``thoughts/<id>.json``) is the normalized, retained
provenance for one capture. Shape (spec § Thought record)::

    {
      "id", "source": "slack|todoist|voice", "ts",
      "permalink",                       # message URL | task id | gs:// audio
      "raw",                             # text | transcript
      "backfill": bool,                  # ingested in the capture-window backfill pull
      "reacted": bool,                   # loop-closure ✅ landed at the source
      "slack"|"todoist"|"audio": {...},  # source-specific provenance
      "triage": {...} | null,            # filled by `route`
      "route":  {...} | null,            # filled by `route`
      "ingested_at": iso
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config


def _safe_id(thought_id: str) -> str:
    # ids embed a Slack ts (``slack-C…-1787.99``) or a Todoist id — both
    # filesystem-safe already, but normalize just in case.
    return thought_id.replace("/", "_")


def thought_path(thought_id: str) -> Path:
    return config.thoughts_dir() / f"{_safe_id(thought_id)}.json"


def load_thought(thought_id: str) -> dict | None:
    path = thought_path(thought_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def has_thought(thought_id: str) -> bool:
    return thought_path(thought_id).exists()


def write_thought(record: dict) -> None:
    config.ensure_spool()
    thought_path(record["id"]).write_text(json.dumps(record, indent=2))


def load_all_thoughts() -> list[dict]:
    d = config.thoughts_dir()
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def load_state() -> dict:
    path = config.state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(state: dict) -> None:
    config.ensure_spool()
    config.state_path().write_text(json.dumps(state, indent=2))


def update_state(**patch) -> dict:
    state = load_state()
    state.update(patch)
    write_state(state)
    return state
