from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tomllib

SLACK_CHANNEL_ID = "C0B5RUX4P26"
DANIEL_USER_ID = "U0B17JULMCY"
TODOIST_INBOX_ID = "6RJ8MCM4gr9C9WpJ"
BACKFILL_DAYS = 90

@dataclass(frozen=True)
class Config:
    channels: tuple[str, ...] = (SLACK_CHANNEL_ID,)
    reply_on_route: bool = True
    max_model_calls: int = 100
    stale_days: int = 60

def base_dir() -> Path:
    if os.environ.get("MAILROOM_HOME"):
        return Path(os.environ["MAILROOM_HOME"])
    # A workspace-local spool is useful for hermetic workers/gates whose home
    # is mounted read-only. Normal installs have no such directory and retain
    # the documented ~/.mailroom location.
    local = Path.cwd() / ".mailroom"
    return local if local.exists() else Path.home() / ".mailroom"

def thoughts_dir() -> Path: return base_dir() / "thoughts"
def audio_dir() -> Path: return base_dir() / "audio"
def state_path() -> Path: return base_dir() / "state.json"
def config_path() -> Path: return base_dir() / "config.toml"
def digest_path() -> Path: return base_dir() / "digest.md"

DEFAULT_CONFIG = '''# mailroom routing policy — edit here, not in code.
[slack]
channels = ["C0B5RUX4P26"]
reply_on_route = true
[triage]
max_model_calls = 100
[todoist]
stale_days = 60
'''

def ensure() -> None:
    thoughts_dir().mkdir(parents=True, exist_ok=True)
    audio_dir().mkdir(parents=True, exist_ok=True)
    if not config_path().exists(): config_path().write_text(DEFAULT_CONFIG)

def load() -> Config:
    ensure()
    try: d = tomllib.loads(config_path().read_text())
    except (OSError, ValueError): return Config()
    slack, triage, todo = d.get("slack", {}), d.get("triage", {}), d.get("todoist", {})
    return Config(tuple(slack.get("channels", [SLACK_CHANNEL_ID])), bool(slack.get("reply_on_route", True)), int(triage.get("max_model_calls", 100)), int(todo.get("stale_days", 60)))
