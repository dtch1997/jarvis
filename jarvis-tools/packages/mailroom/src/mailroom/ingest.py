"""``mailroom ingest`` — pull captures from Slack + Todoist into the spool.

Incremental (per-source cursor in ``state.json``) and idempotent: a capture
that already has a thought record is skipped, so a no-change re-run does nothing
and makes **no model calls** (triage lives in ``route``). Loop closure lands
here: each ingested Slack message gets a ✅ reaction. Voice clips are
transcribed once (Parakeet) and cached.

``ingest_check`` is the gate hook: it re-lists the sources since backfill start
and fails unless every current source item already has a record (i.e. a re-run
would be a no-op) — no model calls, no transcription.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, slack, spool, todoist, voice


@dataclass
class IngestResult:
    slack_new: int = 0
    slack_skipped: int = 0
    voice_transcribed: int = 0
    todoist_new: int = 0
    todoist_skipped: int = 0
    reactions: int = 0
    backfill: bool = False
    errors: list[str] = field(default_factory=list)

    def report(self) -> str:
        return (
            f"ingest ({'backfill' if self.backfill else 'incremental'}): "
            f"slack +{self.slack_new} ({self.slack_skipped} known, "
            f"{self.voice_transcribed} voice), "
            f"todoist +{self.todoist_new} ({self.todoist_skipped} known), "
            f"{self.reactions} ✅ reaction(s)"
            + (f"; {len(self.errors)} error(s)" if self.errors else "")
        )


def _backfill_start(now: datetime, days: int) -> float:
    return (now - timedelta(days=days)).timestamp()


def _within_window(ts_raw, now: datetime, days: int) -> bool:
    """True if a source timestamp falls inside the capture window (or can't be
    parsed — never silently drop an item just because its timestamp is odd)."""
    if not isinstance(ts_raw, str) or not ts_raw:
        return True
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp() >= _backfill_start(now, days)


# --------------------------------------------------------------------------- #
# Slack leg
# --------------------------------------------------------------------------- #
def _ingest_voice(cap: slack.Capture, *, client, transcriber, res: IngestResult) -> dict:
    """Download + transcribe the first audio file on a capture."""
    audio_file = next((f for f in cap.files if str(f.get("mimetype", "")).startswith("audio/")), None)
    config.ensure_spool()
    audio = {}
    raw = cap.text.strip()
    if audio_file:
        url = audio_file.get("url_private_download") or audio_file.get("url_private")
        ext = "." + (audio_file.get("filetype") or "m4a")
        local = config.audio_dir() / f"{cap.id}{ext}"
        try:
            local.write_bytes(client.download(url))
            vr = voice.process_audio(
                local, cap.id, transcriber=transcriber,
                slack_transcription=voice.slack_transcription_text(audio_file),
                duration_ms=audio_file.get("duration_ms"))
            raw = vr.transcript or raw
            audio = {
                "gs": vr.gcs_pointer, "local": vr.local_path,
                "slack_transcription": vr.slack_transcription,
                "duration_ms": vr.duration_ms, "file_id": audio_file.get("id"),
            }
            res.voice_transcribed += 1
        except Exception as e:  # never let one clip kill the sweep
            res.errors.append(f"voice {cap.id}: {e}")
    return {"raw": raw, "audio": audio}


def _ingest_slack_channel(channel: str, *, client, transcriber, backfill: bool,
                          react: bool, now: datetime, res: IngestResult) -> str:
    state = spool.load_state()
    cursors = state.get("slack") or {}
    prev = cursors.get(channel) or {}
    if backfill or not prev.get("last_ts"):
        oldest = f"{_backfill_start(now, config.load_config().backfill_days):.6f}"
        is_backfill = True
    else:
        oldest = prev["last_ts"]
        is_backfill = False

    max_ts = float(prev.get("last_ts") or 0.0)
    base_url = client.workspace_url()  # fetched once; permalinks built locally
    for cap in slack.collect_captures(client, channel, oldest=oldest):
        max_ts = max(max_ts, float(cap.ts))
        if spool.has_thought(cap.id):
            res.slack_skipped += 1
            continue
        payload = _ingest_voice(cap, client=client, transcriber=transcriber, res=res) \
            if cap.is_audio else {"raw": cap.text.strip(), "audio": {}}
        reacted = False
        if react:
            try:
                reacted = client.add_reaction(channel, cap.ts)
                if reacted:
                    res.reactions += 1
            except Exception as e:
                res.errors.append(f"react {cap.id}: {e}")
        record = {
            "id": cap.id,
            "source": "voice" if cap.is_audio else "slack",
            "ts": datetime.fromtimestamp(float(cap.ts), timezone.utc).isoformat(),
            "permalink": slack.build_permalink(base_url, channel, cap.ts),
            "raw": payload["raw"],
            "backfill": is_backfill,
            "reacted": reacted,
            "slack": {"channel": channel, "ts": cap.ts,
                      "has_files": bool(cap.files), "n_files": len(cap.files)},
            "triage": None, "route": None,
            "ingested_at": now.isoformat(),
        }
        if payload["audio"]:
            record["audio"] = payload["audio"]
        spool.write_thought(record)
        res.slack_new += 1

    cursors[channel] = {"last_ts": f"{max_ts:.6f}" if max_ts else oldest}
    spool.update_state(slack=cursors,
                       backfill_start_ts=state.get("backfill_start_ts")
                       or f"{_backfill_start(now, config.load_config().backfill_days):.6f}")
    return channel


# --------------------------------------------------------------------------- #
# Todoist leg
# --------------------------------------------------------------------------- #
def _ingest_todoist(*, client: todoist.TodoistClient, now: datetime,
                    res: IngestResult) -> None:
    window_days = config.load_config().backfill_days
    tasks = client.inbox_tasks()
    for t in tasks:
        tid = f"todoist-{t['id']}"
        if spool.has_thought(tid):
            res.todoist_skipped += 1
            continue
        if not _within_window(t.get("created_at") or t.get("added_at"),
                              now, window_days):
            res.todoist_skipped += 1  # older than the capture window — leave it
            continue
        content = t.get("content") or ""
        desc = t.get("description") or ""
        record = {
            "id": tid,
            "source": "todoist",
            "ts": t.get("created_at") or t.get("added_at") or now.isoformat(),
            "permalink": t.get("url") or f"todoist:task/{t['id']}",
            "raw": (content + ("\n\n" + desc if desc else "")).strip(),
            "backfill": False,
            "reacted": False,
            "todoist": {"task_id": t["id"], "project_id": t.get("project_id"),
                        "content": content, "description": desc,
                        "labels": list(t.get("labels") or [])},
            "triage": None, "route": None,
            "ingested_at": now.isoformat(),
        }
        spool.write_thought(record)
        res.todoist_new += 1
    state = spool.load_state()
    td = state.get("todoist") or {}
    if "baseline_inbox" not in td:
        td["baseline_inbox"] = len(tasks)
    td["last_inbox_seen"] = len(tasks)
    spool.update_state(todoist=td)


# --------------------------------------------------------------------------- #
# public entry points
# --------------------------------------------------------------------------- #
def ingest(*, backfill: bool = False, client: slack.SlackClient | None = None,
           todoist_client: todoist.TodoistClient | None = None,
           transcriber=voice.default_transcriber, do_slack: bool = True,
           do_todoist: bool = True, react: bool = True,
           now: datetime | None = None) -> IngestResult:
    now = now or datetime.now(timezone.utc)
    config.ensure_spool()
    cfg = config.load_config()
    res = IngestResult(backfill=backfill)
    if do_slack:
        client = client or slack.SlackClient()
        for channel in cfg.channels:
            try:
                _ingest_slack_channel(channel, client=client, transcriber=transcriber,
                                      backfill=backfill, react=react, now=now, res=res)
                if backfill:
                    res.backfill = True
            except Exception as e:
                res.errors.append(f"slack {channel}: {e}")
    if do_todoist:
        todoist_client = todoist_client or todoist.TodoistClient()
        try:
            _ingest_todoist(client=todoist_client, now=now, res=res)
        except Exception as e:
            res.errors.append(f"todoist: {e}")
    st = spool.load_state()
    st["last_ingest"] = now.isoformat()
    st["ingest"] = {"slack_new": res.slack_new, "todoist_new": res.todoist_new,
                    "voice_transcribed": res.voice_transcribed,
                    "reactions": res.reactions, "backfill": backfill}
    spool.write_state(st)
    return res


def ingest_check(*, client: slack.SlackClient | None = None,
                 todoist_client: todoist.TodoistClient | None = None,
                 now: datetime | None = None) -> tuple[bool, str]:
    """Gate: every current source item since backfill start has a record, so a
    re-run would be a no-op. No model calls, no transcription."""
    now = now or datetime.now(timezone.utc)
    state = spool.load_state()
    if not state or "backfill_start_ts" not in state:
        return False, "no ingest has run (state.json missing backfill_start_ts)"
    cfg = config.load_config()
    problems: list[str] = []
    checked = 0

    client = client or slack.SlackClient()
    start = state["backfill_start_ts"]
    for channel in cfg.channels:
        try:
            caps = slack.collect_captures(client, channel, oldest=start)
        except Exception as e:
            return False, f"ingest --check: slack unreachable ({e})"
        for cap in caps:
            checked += 1
            if not spool.has_thought(cap.id):
                problems.append(f"un-ingested slack msg {cap.ts} in {channel}")

    todoist_client = todoist_client or todoist.TodoistClient()
    try:
        for t in todoist_client.inbox_tasks():
            if not _within_window(t.get("created_at") or t.get("added_at"),
                                  now, cfg.backfill_days):
                continue  # outside the capture window — ingest skips it too
            checked += 1
            if not spool.has_thought(f"todoist-{t['id']}"):
                problems.append(f"un-ingested Inbox item {t['id']}")
    except Exception as e:
        return False, f"ingest --check: todoist unreachable ({e})"

    if problems:
        return False, (f"ingest --check FAIL: {len(problems)} un-ingested item(s) "
                       f"of {checked} checked\n  - " + "\n  - ".join(problems[:20]))
    return True, f"ingest --check OK: {checked} source item(s) all have thought records"
