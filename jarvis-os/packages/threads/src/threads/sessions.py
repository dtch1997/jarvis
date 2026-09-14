"""``threads sessions`` — the deterministic answer to "which JARVIS sessions
are open right now, and what does each one still owe before it can close?"

Everything here is offline and reads files that already exist; no model
calls, no transcript summarisation. The join is:

- **liveness** — the harness session registry ``~/.claude/sessions/<pid>.json``
  (one file per running ``claude``; carries ``sessionId``, tmux pane, the
  session name, and an idle/busy status + timestamp) filtered by "is that PID
  alive". This is the source of truth for *how many* sessions are open.
- **identity** — a declaration ``~/.threads/sessions/<session-id>.json``
  (``threads declare``, the self-declaration convention) when one exists,
  else the registry name (derived names like ``jarvis-os-c0`` are flagged
  ``undeclared``).
- **obligations** — the statusline wrap-up flags
  ``~/.claude/statusline/sessions/<session-id>.json``, plus ``pr-link`` and
  ``Artifact`` publish records found in the transcript.
- **last real activity** — the last user/assistant turn in the transcript
  (transcript *mtime* is meaningless: housekeeping records keep touching
  files for days after the last turn), or a ``turn_ended`` event once the
  hooks land.
- **parking** — the newest ``threads note`` on the declared slug, or any note
  whose frontmatter names this session.

Each open session gets one verdict, applied in this order:

1. ``busy``       — the harness says the session is mid-turn; leave it.
2. ``recent``     — idle for less than ``--idle-hours`` (default 12); leave it.
3. ``needs-park`` — idle with open flags, *or* with a PR / artifact that no
   later note accounts for. Something must be written down before closing.
4. ``closable``   — idle, no flags, and either a note newer than the last
   turn or nothing to account for at all.

``--all`` also lists registry entries whose PID is gone (``gone``: a stale
registry file, harmless). The current session is excluded unless
``--include-self``.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .transcripts import _is_tool_result_only, _parse_ts

DEFAULT_IDLE_HOURS = 12
_VERDICT_ORDER = {"needs-park": 0, "closable": 1, "recent": 2, "busy": 3, "gone": 4}


# ----------------------------------------------------------------- inputs --

def registry_dir() -> Path:
    override = os.environ.get("THREADS_CLAUDE_SESSIONS_DIR")
    return Path(override) if override else Path.home() / ".claude" / "sessions"


def statusline_dir() -> Path:
    override = os.environ.get("THREADS_STATUSLINE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "statusline" / "sessions"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    # a zombie has exited; the harness will not append to its transcript again
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[-1].split()[0] != "Z"
    except OSError:
        return True


def _ms(value) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    return None


def self_session_id() -> str | None:
    """The calling session, from the env or by walking up to the ``claude``
    ancestor and matching its PID in the registry."""
    for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        v = os.environ.get(k)
        if v:
            return v
    pid = os.getppid()
    by_pid = {}
    for rec in _load_registry_raw():
        try:
            by_pid[int(rec.get("pid"))] = rec.get("sessionId")
        except (TypeError, ValueError):
            pass
    for _ in range(64):
        if pid <= 1:
            break
        if pid in by_pid:
            return by_pid[pid]
        try:
            with open(f"/proc/{pid}/stat") as f:
                pid = int(f.read().rsplit(")", 1)[-1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return None


def _load_registry_raw() -> list[dict]:
    out = []
    d = registry_dir()
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("sessionId"):
            out.append(rec)
    return out


def _load_declaration(session_id: str) -> dict | None:
    p = config.declarations_dir() / f"{session_id}.json"
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) else None


def _load_statusline(session_id: str) -> tuple[str | None, list[str]]:
    p = statusline_dir() / f"{session_id}.json"
    if not p.is_file():
        return None, []
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return None, []
    if not isinstance(rec, dict):
        return None, []
    flags = [f for f in rec.get("flags") or [] if isinstance(f, str) and f.strip()]
    topic = rec.get("topic")
    return (topic if isinstance(topic, str) and topic.strip() else None), flags


def find_transcript(session_id: str) -> Path | None:
    root = config.projects_dir()
    if not root.is_dir():
        return None
    return next(iter(sorted(root.glob(f"*/{session_id}.jsonl"))), None)


@dataclass
class TranscriptFacts:
    last_turn: datetime | None = None
    last_user: str | None = None
    n_user_turns: int = 0
    prs: list[str] = field(default_factory=list)
    artifacts: int = 0
    parse_warnings: int = 0


def scan_transcript(path: Path) -> TranscriptFacts:
    """One forward pass; only lines that can carry a turn, a PR link, or an
    artifact publish are JSON-parsed (the rest are progress/ledger records)."""
    facts = TranscriptFacts()
    try:
        fh = open(path, errors="ignore")
    except OSError:
        return facts
    with fh:
        for line in fh:
            if '"role"' not in line and "pr-link" not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                facts.parse_warnings += 1
                continue
            if not isinstance(o, dict):
                continue
            if o.get("type") == "pr-link":
                url = o.get("prUrl")
                if isinstance(url, str) and url not in facts.prs:
                    facts.prs.append(url)
                continue
            msg = o.get("message")
            if not isinstance(msg, dict) or o.get("isMeta"):
                continue
            role = msg.get("role")
            content = msg.get("content")
            ts = _parse_ts(o.get("timestamp"))
            if role == "user":
                if _is_tool_result_only(content):
                    continue
                text = content if isinstance(content, str) else " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ) if isinstance(content, list) else ""
                text = " ".join(text.split())
                if text.startswith("<") and text.endswith(">"):
                    continue  # command / notification envelopes are not turns
                facts.n_user_turns += 1
                facts.last_user = text[:160] or facts.last_user
            elif role == "assistant":
                if isinstance(content, list):
                    for b in content:
                        if (isinstance(b, dict) and b.get("type") == "tool_use"
                                and b.get("name") == "Artifact"):
                            inp = b.get("input") or {}
                            if not isinstance(inp, dict):
                                continue
                            if inp.get("action", "publish") == "publish" and inp.get("file_path"):
                                facts.artifacts += 1
            else:
                continue
            if ts and (facts.last_turn is None or ts > facts.last_turn):
                facts.last_turn = ts
    return facts


def _latest_note(session_id: str, slug: str | None) -> tuple[datetime | None, str | None, str | None]:
    """Newest note on ``slug`` or naming this session: (created, status, slug)."""
    from .note import load_notes
    best: tuple[datetime | None, str | None, str | None] = (None, None, None)
    for rec in load_notes():
        if rec.get("slug") != slug and rec.get("session_id") != session_id:
            continue
        created = _parse_ts(rec.get("created"))
        if created and (best[0] is None or created > best[0]):
            best = (created, rec.get("status"), rec.get("slug"))
    return best


# ----------------------------------------------------------------- output --

@dataclass
class OpenSession:
    session_id: str
    pid: int
    alive: bool
    name: str
    name_source: str
    tmux: str | None
    cwd: str | None
    kind: str
    started: datetime | None
    harness_status: str | None
    status_at: datetime | None
    slug: str | None
    intent: str | None
    declared: bool
    topic: str | None
    flags: list[str]
    transcript: str | None
    last_turn: datetime | None
    last_user: str | None
    n_user_turns: int
    prs: list[str]
    artifacts: int
    last_note: datetime | None
    last_note_status: str | None
    note_slug: str | None
    idle_hours: float
    verdict: str
    reason: str

    @property
    def label(self) -> str:
        return self.slug or self.name

    def to_json(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d


def _idle_hours(last_turn, status_at, started, now) -> float:
    ref = last_turn or status_at or started
    if ref is None:
        return 0.0
    return max(0.0, (now - ref).total_seconds() / 3600.0)


def classify(*, alive: bool, harness_status: str | None, idle_hours: float,
             flags: list[str], prs: list[str], artifacts: int,
             last_turn: datetime | None, last_note: datetime | None,
             idle_threshold: float) -> tuple[str, str]:
    if not alive:
        return "gone", "registry entry for a dead PID"
    if harness_status == "busy":
        return "busy", "mid-turn"
    if idle_hours < idle_threshold:
        return "recent", f"idle {idle_hours:.1f}h < {idle_threshold:g}h"
    if flags:
        return "needs-park", f"{len(flags)} open flag(s)"
    obligations = bool(prs) or artifacts > 0
    noted_after = bool(last_note and (last_turn is None or last_note >= last_turn))
    if obligations and not noted_after:
        what = " + ".join(x for x in (
            f"{len(prs)} PR(s)" if prs else "", f"{artifacts} artifact(s)" if artifacts else "") if x)
        return "needs-park", f"{what} with no note since the last turn"
    if noted_after:
        return "closable", "note newer than last turn, no flags"
    return "closable", "no flags, no PRs, no artifacts"


def open_sessions(*, now: datetime | None = None, alive=None,
                  include_self: bool = False, include_gone: bool = False,
                  idle_hours: float = DEFAULT_IDLE_HOURS) -> list[OpenSession]:
    now = now or datetime.now(timezone.utc)
    alive = alive or _pid_alive
    me = None if include_self else self_session_id()
    out: list[OpenSession] = []
    for rec in _load_registry_raw():
        sid = rec["sessionId"]
        if me and sid == me:
            continue
        try:
            pid = int(rec.get("pid"))
        except (TypeError, ValueError):
            continue
        is_alive = bool(alive(pid))
        if not is_alive and not include_gone:
            continue
        decl = _load_declaration(sid) or {}
        topic, flags = _load_statusline(sid)
        tpath = find_transcript(sid)
        facts = scan_transcript(tpath) if tpath else TranscriptFacts()
        slug = decl.get("slug") if isinstance(decl.get("slug"), str) else None
        note_at, note_status, note_slug = _latest_note(sid, slug)
        status_at = _ms(rec.get("statusUpdatedAt")) or _ms(rec.get("updatedAt"))
        started = _ms(rec.get("startedAt"))
        idle = _idle_hours(facts.last_turn, status_at, started, now)
        verdict, reason = classify(
            alive=is_alive, harness_status=rec.get("status"), idle_hours=idle,
            flags=flags, prs=facts.prs, artifacts=facts.artifacts,
            last_turn=facts.last_turn, last_note=note_at, idle_threshold=idle_hours)
        out.append(OpenSession(
            session_id=sid, pid=pid, alive=is_alive,
            name=str(rec.get("name") or sid[:8]),
            name_source=str(rec.get("nameSource") or "unknown"),
            tmux=rec.get("tmux"), cwd=rec.get("cwd"),
            kind=str(decl.get("kind") or rec.get("kind") or "interactive"),
            started=started, harness_status=rec.get("status"), status_at=status_at,
            slug=slug, intent=decl.get("intent") if isinstance(decl.get("intent"), str) else None,
            declared=bool(slug), topic=topic, flags=flags,
            transcript=str(tpath) if tpath else None,
            last_turn=facts.last_turn, last_user=facts.last_user,
            n_user_turns=facts.n_user_turns, prs=facts.prs, artifacts=facts.artifacts,
            last_note=note_at, last_note_status=note_status, note_slug=note_slug,
            idle_hours=idle, verdict=verdict, reason=reason,
        ))
    out.sort(key=lambda s: (_VERDICT_ORDER.get(s.verdict, 9), -s.idle_hours))
    return out


def _fmt_idle(h: float) -> str:
    if h < 1:
        return f"{int(h * 60)}m"
    if h < 48:
        return f"{h:.0f}h"
    return f"{int(h // 24)}d{int(h % 24)}h"


def render(sessions: list[OpenSession], *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}
    for s in sessions:
        counts[s.verdict] = counts.get(s.verdict, 0) + 1
    head = ", ".join(f"{counts[k]} {k}" for k in _VERDICT_ORDER if k in counts) or "none"
    lines = [f"open sessions ({now.astimezone().strftime('%H:%M')}): {len(sessions)} — {head}", ""]
    if not sessions:
        return "\n".join(lines)
    rows = []
    for s in sessions:
        label = s.label if s.declared or s.name_source == "user" else f"{s.name} (undeclared)"
        pane = (s.tmux or "").split(":")[0] or "-"
        note = (_fmt_idle((now - s.last_note).total_seconds() / 3600) + " ago"
                + (f" [{s.last_note_status}]" if s.last_note_status else "")) if s.last_note else "-"
        rows.append((s.verdict, label, _fmt_idle(s.idle_hours), pane, str(len(s.flags)),
                     str(len(s.prs)), str(s.artifacts), note, s.session_id[:8], s.reason))
    hdr = ("verdict", "session", "idle", "pane", "flags", "PRs", "art", "last note", "id", "why")
    widths = [max(len(str(r[i])) for r in [hdr, *rows]) for i in range(len(hdr) - 1)]
    def fmt(r):
        return "  ".join(str(r[i]).ljust(widths[i]) for i in range(len(widths))) + "  " + r[-1]
    lines.append(fmt(hdr))
    lines.append(fmt(tuple("-" * w for w in widths) + ("-" * 3,)))
    lines.extend(fmt(r) for r in rows)
    detail = [s for s in sessions if s.verdict == "needs-park"]
    if detail:
        lines.append("")
        lines.append("needs-park detail:")
        for s in detail:
            lines.append(f"  {s.label} ({s.session_id[:8]}):")
            if s.topic:
                lines.append(f"    topic: {s.topic}")
            for f in s.flags:
                lines.append(f"    flag:  {f}")
            for u in s.prs:
                lines.append(f"    pr:    {u}")
            if s.artifacts:
                lines.append(f"    artifacts published: {s.artifacts}")
            if s.last_user:
                lines.append(f"    last user turn: {s.last_user[:120]}")
            lines.append(f"    park with: threads note {s.slug or s.note_slug or '<slug>'} - --status parked")
    return "\n".join(lines)
