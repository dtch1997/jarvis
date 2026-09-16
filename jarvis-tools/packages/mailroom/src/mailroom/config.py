"""mailroom config + spool paths.

The spool lives under ``~/.mailroom/`` (override the whole base with
``MAILROOM_HOME`` — tests and smoke runs point it at a scratch dir so they
never touch the real spool). The spool is *retained provenance*, not a cache:
sources age out (Slack history) or get drained (Todoist Inbox), so the thought
records are the durable copy.

The actuator targets are overridable too, so tests can point at fixture trees
without monkeypatching ``Path.home``:

- ``MAILROOM_GOALS_DIR`` — the ``jarvis/goals`` tree (goal-signal bullets).

Credentials come from the environment only (``~/.env`` sourced per shell):
``SLACK_MAILROOM_TOKEN``, ``TODOIST_API_TOKEN``, ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

try:  # py3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

# defaults (also documented in the README)
# capture window: thoughts older than this are not worth capturing (Daniel,
# 2026-08-18: "not necessary to capture stuff more than 3 weeks old") — applies
# to the Slack backfill AND the Todoist Inbox pull.
DEFAULT_BACKFILL_DAYS = 21
DEFAULT_MAX_CALLS = 200
DEFAULT_TRIAGE_BATCH = 8
DEFAULT_STALE_DAYS = 60
MODEL = "claude-haiku-4-5-20251001"

# rough haiku pricing — used only for a spend *estimate* when a runner does not
# report a real cost.
EST_USD_PER_CALL = 0.004

# verified environment facts (spec, 2026-08-18)
DANIEL_USER_ID = "U0B17JULMCY"
BOT_USER_ID = "U0BQWRJETGR"
DEFAULT_SLACK_CHANNEL = "C0B5RUX4P26"  # #lab-notes-daniel (private)
TODOIST_INBOX_ID = "6RJ8MCM4gr9C9WpJ"
GCS_AUDIO_PREFIX = "gcs:alignment-team-general-storage/daniel/jarvis/mailroom/audio"

# the curated Todoist projects a thought may be filed into (name → id), verified
# live 2026-08-18. Inbox is the source, never a destination.
TODOIST_PROJECTS = {
    "Focus Areas": "6gx7MHMggqg8VQCf",
    "Automation": "6h3xFGvP43CH3m4R",
    "Habits": "6fPV5WGFR72Cjc84",
    "Writing": "6gx7MF4Wjfh2J66f",
    "Investment": "6gwfrPpMFCXmhJ46",
    "Fitness": "6gx76m23Cw3399w5",
    "PhD": "6gwfrHfh5fwJWFWH",
    "Media": "6fHPFjj77fMv54F4",
    "Papers to read": "6gwgM5MHRH4hFcgW",
    "Dating": "6gwqvh2XCq29Hwjh",
    "Tools": "6gx79R3RgjcqWc7c",
    "French": "6h2589V6pm8wjjcj",
}
PAPERS_PROJECT = "Papers to read"


def _home() -> Path:
    return Path(os.environ.get("MAILROOM_HOME") or Path.home())


def mailroom_dir() -> Path:
    return _home() / ".mailroom"


def thoughts_dir() -> Path:
    return mailroom_dir() / "thoughts"


def audio_dir() -> Path:
    return mailroom_dir() / "audio"


def state_path() -> Path:
    return mailroom_dir() / "state.json"


def config_path() -> Path:
    return mailroom_dir() / "config.toml"


def voicedocs_dir() -> Path:
    """voicedoc leg: per-clip provenance records + staged HTML uploads."""
    return mailroom_dir() / "voicedocs"


def goals_dir() -> Path:
    """The ``jarvis/goals`` tree (goal-signal bullets land here)."""
    override = os.environ.get("MAILROOM_GOALS_DIR")
    if override:
        return Path(override)
    return Path.home() / "jarvis" / "goals"


# --------------------------------------------------------------------------- #
# config.toml — tunable knobs (config-first: routing corrections are config
# edits, not code). Written with defaults on first run, never overwritten.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VoicedocConfig:
    """The voicedoc leg (voice note → work-Drive Google Doc + Slack draft)."""
    enabled: bool = True
    channel: str = DEFAULT_SLACK_CHANNEL        # capture: audio clips here
    draft_channel: str = DEFAULT_SLACK_CHANNEL  # draft posts land here
    drive_remote: str = "gdrive-work:"          # rclone drive: remote (work acct)
    drive_folder: str = ""                      # path under the remote root
    model: str = "claude-sonnet-5"              # transcript-cleanup model
    poll_seconds: int = 20


@dataclass(frozen=True)
class Config:
    channels: list[str] = field(default_factory=lambda: [DEFAULT_SLACK_CHANNEL])
    reply_on_route: bool = True
    backfill_days: int = DEFAULT_BACKFILL_DAYS
    stale_days: int = DEFAULT_STALE_DAYS
    max_calls: int = DEFAULT_MAX_CALLS
    triage_batch: int = DEFAULT_TRIAGE_BATCH
    route_threshold: float = 0.80  # >= this fraction non-unclear for route --check
    voicedoc: VoicedocConfig = field(default_factory=VoicedocConfig)


DEFAULT_CONFIG_TOML = """\
# mailroom config — tunable knobs. Routing is config-first: corrections
# (a channel added, reply_on_route flipped, a threshold nudged) are edits here,
# not code changes. Delete a line to fall back to the built-in default.

# Slack channels ingested (by channel id). Adding a channel is a config edit.
channels = ["C0B5RUX4P26"]     # #lab-notes-daniel

# post a short threaded reply saying where a thought went, on *newly-ingested*
# messages in incremental runs (never on the backfill).
reply_on_route = true

# capture window (days): the first Slack pull backfills this far, and older
# Todoist Inbox items are left where they are (not worth capturing).
backfill_days = 21

# stale-sweep: items in curated projects untouched this long are listed in the
# digest as prune candidates (propose-only; mailroom never closes them).
stale_days = 60

# per-run triage model-call cap (a batch counts as one call), and thoughts per
# batched claude -p call.
max_calls = 200
triage_batch = 8

# route --check passes only if this fraction of thoughts are routed (not unclear).
route_threshold = 0.80
"""

# appended to an existing config.toml that predates the voicedoc leg (additive,
# never rewrites what's there) — also the tail of DEFAULT_CONFIG_TOML.
VOICEDOC_CONFIG_TOML = """\

[voicedoc]
# voice note → cleaned Google Doc on the work Drive + forwardable Slack draft.
# All knobs are config-first: retarget the folder or channels by editing here.
enabled = true
channel = "C0B5RUX4P26"        # capture: Daniel's audio clips in #lab-notes-daniel
draft_channel = "C0B5RUX4P26"  # where the title+TL;DR+link draft is posted
drive_remote = "gdrive-work:"  # rclone drive remote on the WORK Google account
drive_folder = ""              # path under the remote root ("" = the root itself)
model = "claude-sonnet-5"      # transcript-cleanup model (quality > cost here)
poll_seconds = 20              # watcher poll interval
"""

DEFAULT_CONFIG_TOML += VOICEDOC_CONFIG_TOML


def _coerce(v, default):
    if v is None:
        return default
    try:
        return type(default)(v)
    except (TypeError, ValueError):
        return default


def load_config() -> Config:
    base = Config()
    path = config_path()
    if tomllib is None or not path.exists():
        return base
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, ValueError):
        return base
    channels = data.get("channels")
    if not isinstance(channels, list) or not channels:
        channels = base.channels
    else:
        channels = [str(c) for c in channels]
    vd_base = base.voicedoc
    vd_data = data.get("voicedoc") if isinstance(data.get("voicedoc"), dict) else {}
    voicedoc = replace(
        vd_base,
        enabled=bool(vd_data.get("enabled", vd_base.enabled)),
        channel=str(vd_data.get("channel") or vd_base.channel),
        draft_channel=str(vd_data.get("draft_channel") or vd_base.draft_channel),
        drive_remote=str(vd_data.get("drive_remote") or vd_base.drive_remote),
        drive_folder=str(vd_data.get("drive_folder", vd_base.drive_folder)),
        model=str(vd_data.get("model") or vd_base.model),
        poll_seconds=_coerce(vd_data.get("poll_seconds"), vd_base.poll_seconds),
    )
    return replace(
        base,
        channels=channels,
        reply_on_route=bool(data.get("reply_on_route", base.reply_on_route)),
        backfill_days=_coerce(data.get("backfill_days"), base.backfill_days),
        stale_days=_coerce(data.get("stale_days"), base.stale_days),
        max_calls=_coerce(data.get("max_calls"), base.max_calls),
        triage_batch=_coerce(data.get("triage_batch"), base.triage_batch),
        route_threshold=_coerce(data.get("route_threshold"), base.route_threshold),
        voicedoc=voicedoc,
    )


def ensure_spool() -> None:
    for d in (mailroom_dir(), thoughts_dir(), audio_dir(), voicedocs_dir()):
        d.mkdir(parents=True, exist_ok=True)
    path = config_path()
    try:
        if not path.exists():
            path.write_text(DEFAULT_CONFIG_TOML)
        elif "[voicedoc]" not in path.read_text():
            # additive migration for spools that predate the voicedoc leg —
            # existing knobs are never rewritten.
            with path.open("a") as fh:
                fh.write(VOICEDOC_CONFIG_TOML)
    except OSError:
        pass
