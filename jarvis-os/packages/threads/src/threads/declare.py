"""Session self-declaration + the per-session event log.

A JARVIS session declares which thread it is at the top
(``threads declare <slug> "<intent>"``). From then on the session is
addressable by thread, not by a derived name like ``jarvis-os-c0``, and
``threads sessions`` / the board can say what it is and what it still owes.

Files, both under ``~/.threads/sessions/`` (``config.declarations_dir()``):

- ``<session-id>.json`` — the declaration: slug, intent, kind
  (interactive | concierge | cron | subagent), tmux pane, cwd, branch,
  ``declared_at``; plus ``supersedes`` (the previous declaration in the same
  pane, set on ``/clear``), ``superseded_by`` and ``closed_at`` once the
  session is over.
- ``<session-id>.events.jsonl`` — one JSON line per lifecycle event:
  ``declared`` / ``redeclared`` / ``resumed`` / ``compacted`` /
  ``turn_ended`` / ``superseded`` / ``closed`` / ``note``. Hooks append most
  of these (``threads hook``), so an agent only ever runs ``declare``.

Identity is the harness session id. ``/clear`` gives a pane a *new* session
id, so a cleared pane is a new session and gets a new declaration; the old
one is marked superseded with a pointer forward, keeping the pane's history
a chain.

Side effects of ``declare`` (best-effort, never fatal, off under
``THREADS_NO_SIDE_EFFECTS=1``): rename the tmux window to the slug and set
the statusline topic row to ``slug — intent``. The harness's own session
name is not touched (no supported write path); the declaration is the
identity.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config

KINDS = ("interactive", "concierge", "cron", "subagent")


def declaration_path(session_id: str) -> Path:
    return config.declarations_dir() / f"{session_id}.json"


def events_path(session_id: str) -> Path:
    return config.declarations_dir() / f"{session_id}.events.jsonl"


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def validate_slug(slug: str) -> str:
    slug = (slug or "").strip().lower()
    if not slug or any(c in slug for c in "/\\ \t") or slug.startswith("."):
        raise ValueError(f"bad slug: {slug!r} (use a kebab-case memory-stub name)")
    return slug


def current_session_id() -> str | None:
    for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        v = os.environ.get(k)
        if v:
            return v
    from .sessions import self_session_id
    return self_session_id()


# ------------------------------------------------------------------ events --

def append_event(session_id: str, event: str, *, now: datetime | None = None,
                 **fields) -> bool:
    """Append one event line. Returns False (never raises) on any failure —
    hooks call this and must not wedge a session."""
    try:
        p = events_path(session_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"t": _iso(_now(now)), "event": event, **fields}
        with open(p, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def load_events(session_id: str) -> list[dict]:
    p = events_path(session_id)
    out: list[dict] = []
    if not p.is_file():
        return out
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if isinstance(o, dict) and o.get("event"):
                out.append(o)
    except OSError:
        pass
    return out


def last_event(session_id: str, event: str) -> dict | None:
    hits = [e for e in load_events(session_id) if e.get("event") == event]
    return hits[-1] if hits else None


# ------------------------------------------------------------ declarations --

def load_declaration(session_id: str) -> dict | None:
    p = declaration_path(session_id)
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) and rec.get("slug") else None


def _write_declaration(rec: dict) -> Path:
    p = declaration_path(rec["session_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, p)
    return p


def iter_declarations() -> list[dict]:
    d = config.declarations_dir()
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        if p.name.endswith(".tmp"):
            continue
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("slug") and rec.get("session_id"):
            out.append(rec)
    return out


def is_open(rec: dict) -> bool:
    return not rec.get("closed_at") and not rec.get("superseded_by")


# ------------------------------------------------------------------- pane --

def _registry_pane(session_id: str) -> str | None:
    from .sessions import _load_registry_raw
    for rec in _load_registry_raw():
        if rec.get("sessionId") == session_id and isinstance(rec.get("tmux"), str):
            return rec["tmux"]
    return None


def current_pane(session_id: str | None = None) -> str | None:
    """``session:@window.%pane`` for this session — from the harness registry,
    else from ``$TMUX_PANE`` via tmux."""
    if session_id:
        pane = _registry_pane(session_id)
        if pane:
            return pane
    tp = os.environ.get("TMUX_PANE")
    if tp and shutil.which("tmux"):
        try:
            out = subprocess.run(
                ["tmux", "display-message", "-p", "-t", tp,
                 "#{session_name}:#{window_id}.#{pane_id}"],
                capture_output=True, text=True, timeout=3)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None


def _window_of(pane: str | None) -> str | None:
    # "jarvis-3:@2.%2" -> "@2"
    if not pane or ":" not in pane:
        return None
    win = pane.split(":", 1)[1].split(".", 1)[0]
    return win if win.startswith("@") else None


def _side_effects_enabled() -> bool:
    return os.environ.get("THREADS_NO_SIDE_EFFECTS", "") not in ("1", "true", "yes")


def apply_side_effects(rec: dict) -> list[str]:
    """Rename the tmux window + set the statusline topic. Returns what was
    applied; failures are silent (best-effort)."""
    applied: list[str] = []
    if not _side_effects_enabled():
        return applied
    win = _window_of(rec.get("pane"))
    if win and shutil.which("tmux"):
        try:
            r = subprocess.run(["tmux", "rename-window", "-t", win, rec["slug"]],
                               capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                applied.append("tmux-window")
        except (OSError, subprocess.TimeoutExpired):
            pass
    if shutil.which("claude-statusline"):
        topic = rec["slug"] + (f" — {rec['intent']}" if rec.get("intent") else "")
        try:
            r = subprocess.run(["claude-statusline", "--session", rec["session_id"],
                                "note", topic], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                applied.append("statusline-topic")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return applied


# ---------------------------------------------------------------- actions --

def declare(slug: str, intent: str = "", *, session_id: str | None = None,
            kind: str = "interactive", cwd: str | None = None,
            branch: str | None = None, pane: str | None = None,
            now: datetime | None = None, side_effects: bool = True) -> dict:
    """Write (or re-point) this session's declaration and log the event."""
    slug = validate_slug(slug)
    if kind not in KINDS:
        raise ValueError(f"bad kind: {kind!r} (one of {', '.join(KINDS)})")
    session_id = session_id or current_session_id()
    if not session_id:
        raise ValueError("no session id: pass --session or run inside a Claude Code session")
    now = _now(now)
    cwd = cwd or os.getcwd()
    if branch is None:
        from .note import _git_branch
        branch = _git_branch(cwd)
    pane = pane or current_pane(session_id)
    prev = load_declaration(session_id)
    rec = {
        "session_id": session_id, "slug": slug, "intent": (intent or "").strip(),
        "kind": kind, "pane": pane, "cwd": cwd, "branch": branch,
        "declared_at": _iso(now),
        "supersedes": (prev or {}).get("supersedes"),
    }
    if prev and prev.get("slug") != slug:
        rec["previous_slug"] = prev["slug"]
    _write_declaration(rec)
    if prev:
        append_event(session_id, "redeclared", now=now, slug=slug,
                     from_slug=prev.get("slug"), intent=rec["intent"])
    else:
        append_event(session_id, "declared", now=now, slug=slug, kind=kind,
                     intent=rec["intent"], pane=pane)
    rec["applied"] = apply_side_effects(rec) if side_effects else []
    return rec


def supersede_pane(pane: str | None, new_session_id: str, *,
                   now: datetime | None = None) -> list[dict]:
    """On ``/clear``: every open declaration in ``pane`` from another session
    is marked superseded by ``new_session_id``. Returns them."""
    if not pane:
        return []
    now = _now(now)
    done = []
    for rec in iter_declarations():
        if rec["session_id"] == new_session_id or rec.get("pane") != pane:
            continue
        if not is_open(rec):
            continue
        rec["superseded_by"] = new_session_id
        rec["superseded_at"] = _iso(now)
        _write_declaration(rec)
        append_event(rec["session_id"], "superseded", now=now, by=new_session_id)
        done.append(rec)
    return done


def mark_closed(session_id: str, reason: str = "", *,
                now: datetime | None = None) -> bool:
    now = _now(now)
    rec = load_declaration(session_id)
    if rec and not rec.get("closed_at"):
        rec["closed_at"] = _iso(now)
        if reason:
            rec["closed_reason"] = reason
        try:
            _write_declaration(rec)
        except OSError:
            pass
    return append_event(session_id, "closed", now=now, reason=reason)


def previous_in_pane(pane: str | None, session_id: str) -> dict | None:
    """The most recent declaration this pane carried before ``session_id``
    (superseded or not) — for the /clear nag."""
    if not pane:
        return None
    cands = [r for r in iter_declarations()
             if r.get("pane") == pane and r["session_id"] != session_id]
    if not cands:
        return None
    return max(cands, key=lambda r: r.get("declared_at", ""))


def describe(rec: dict) -> str:
    s = f"{rec['slug']}"
    if rec.get("intent"):
        s += f" — {rec['intent']}"
    return s
