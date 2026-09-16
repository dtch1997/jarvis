"""``threads hook`` — the Claude Code hook entry point for the declaration
convention. One command, dispatched on ``hook_event_name`` from the JSON the
harness passes on stdin. Registered in ``.claude/settings.json`` for
SessionStart, UserPromptSubmit, Stop, and SessionEnd.

Contract (all four): exit 0 always; stdout on SessionStart / UserPromptSubmit
is added to the model's context; any internal error is swallowed (fail open —
never wedge a session over a hook). Set ``THREADS_HOOK_DEBUG=1`` to log
exceptions to ``~/.threads/sessions/hooks.log``.

- **SessionStart** ``source=startup``: auto-declare from ``$THREADS_SLUG``
  (+ ``$THREADS_INTENT``, ``$THREADS_KIND``) when a launcher set them
  (concierge, cron, ``threads launch``); otherwise print the declare nag.
  ``source=clear``: the pane's previous declaration is superseded and the
  nag names it, so the agent can re-declare the same slug or a new one.
  ``source=resume``: log ``resumed`` and restate the declared thread.
  ``source=compact``: log ``compacted``, say nothing.
- **UserPromptSubmit**: one-line nag while undeclared; silent once declared.
- **Stop**: log ``turn_ended`` (the "last real activity" timestamp).
- **SessionEnd**: log ``closed`` and stamp the declaration.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

from . import config, declare

NAG = ("Undeclared session — declare its thread before working: "
       "threads declare <slug> \"<one-line intent>\"  "
       "(slug = memory-stub name, or a new kebab-case name; add --kind "
       "concierge|cron|subagent when not interactive).")


def _log(msg: str) -> None:
    if os.environ.get("THREADS_HOOK_DEBUG"):
        try:
            p = config.declarations_dir() / "hooks.log"
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a") as f:
                f.write(msg.rstrip() + "\n")
        except OSError:
            pass


def _auto_declare(sid: str, cwd: str | None, pane: str | None) -> dict | None:
    slug = os.environ.get("THREADS_SLUG")
    if not slug:
        return None
    kind = os.environ.get("THREADS_KIND") or "concierge"
    if kind not in declare.KINDS:
        kind = "concierge"
    try:
        return declare.declare(slug, os.environ.get("THREADS_INTENT", ""),
                               session_id=sid, kind=kind, cwd=cwd, pane=pane)
    except ValueError:
        return None


def on_session_start(data: dict) -> str:
    sid = data.get("session_id") or ""
    if not sid:
        return ""
    source = data.get("source") or "startup"
    cwd = data.get("cwd")
    pane = declare.current_pane(sid)
    current = declare.load_declaration(sid)
    if source == "compact":
        declare.append_event(sid, "compacted")
        return ""
    if source == "resume":
        declare.append_event(sid, "resumed", pane=pane)
        if current:
            if pane and current.get("pane") != pane:
                current["pane"] = pane
                declare._write_declaration(current)
            declare.apply_side_effects(current)
            return (f"Declared thread: {declare.describe(current)}. "
                    f"`threads pickup {current['slug']}` prints the context pack.")
        return NAG
    # startup or clear
    if current:
        return ""
    auto = _auto_declare(sid, cwd, pane)
    if auto:
        return f"Declared thread (from launcher env): {declare.describe(auto)}."
    if source == "clear":
        prev = declare.previous_in_pane(pane, sid)
        declare.supersede_pane(pane, sid)
        if prev:
            return (f"This pane was on thread `{prev['slug']}`"
                    f"{' — ' + prev['intent'] if prev.get('intent') else ''} "
                    f"(now superseded by this session). Declare the new thread: "
                    f"`threads declare {prev['slug']} \"<intent>\"` to continue it, "
                    f"or a different slug to start something else.")
    return NAG


def on_user_prompt(data: dict) -> str:
    sid = data.get("session_id") or ""
    if not sid or declare.load_declaration(sid):
        return ""
    return NAG


def on_stop(data: dict) -> str:
    sid = data.get("session_id") or ""
    if sid:
        declare.append_event(sid, "turn_ended")
    return ""


def on_session_end(data: dict) -> str:
    sid = data.get("session_id") or ""
    if sid:
        declare.mark_closed(sid, data.get("reason") or "")
    return ""


_DISPATCH = {
    "SessionStart": on_session_start,
    "UserPromptSubmit": on_user_prompt,
    "Stop": on_stop,
    "SessionEnd": on_session_end,
}


def run(event: str | None = None, stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        raw = stdin.read()
        data = json.loads(raw) if raw and raw.strip() else {}
        if not isinstance(data, dict):
            data = {}
        name = data.get("hook_event_name") or event or ""
        fn = _DISPATCH.get(name)
        if fn is None:
            return 0
        out = fn(data)
        if out:
            stdout.write(out.rstrip() + "\n")
    except Exception:  # noqa: BLE001 — fail open by contract
        _log(traceback.format_exc())
    return 0
