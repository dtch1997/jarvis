"""declare + hooks: the self-declaration layer (offline, no tmux, no statusline)."""

from __future__ import annotations

import io
import json
import os
from datetime import timedelta

import pytest

from threads import config, declare, hooks, note, sessions
from threads.cli import main

from conftest import NOW

PROJECT = "-home-x-jarvis"


def _registry(pid: int, sid: str, *, tmux="jarvis-3:@2.%2", status="idle"):
    d = config.Path(os.environ["THREADS_CLAUDE_SESSIONS_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pid}.json").write_text(json.dumps({
        "pid": pid, "sessionId": sid, "cwd": "/home/x/jarvis",
        "startedAt": int((NOW - timedelta(days=1)).timestamp() * 1000),
        "kind": "interactive", "tmux": tmux, "name": "jarvis-os-zz",
        "nameSource": "derived", "status": status,
        "statusUpdatedAt": int((NOW - timedelta(days=1)).timestamp() * 1000)}))


def _hook(event: str, **data) -> str:
    data.setdefault("hook_event_name", event)
    out = io.StringIO()
    rc = hooks.run(stdin=io.StringIO(json.dumps(data)), stdout=out)
    assert rc == 0
    return out.getvalue()


# ----------------------------------------------------------------- declare --

def test_declare_writes_file_event_and_side_effect_list(env):
    _registry(100, "s1")
    rec = declare.declare("my-thread", "phase 2", session_id="s1", cwd=str(env.root),
                          branch="b", now=NOW)
    assert rec["pane"] == "jarvis-3:@2.%2" and rec["applied"] == []  # side effects off
    on_disk = declare.load_declaration("s1")
    assert on_disk["slug"] == "my-thread" and on_disk["intent"] == "phase 2"
    assert on_disk["branch"] == "b" and on_disk["kind"] == "interactive"
    evs = declare.load_events("s1")
    assert [e["event"] for e in evs] == ["declared"]
    assert evs[0]["slug"] == "my-thread"


def test_redeclare_repoints_and_keeps_previous(env):
    declare.declare("a", "x", session_id="s1", cwd=str(env.root), branch="b", now=NOW)
    rec = declare.declare("b-thread", "y", session_id="s1", cwd=str(env.root),
                          branch="b", now=NOW + timedelta(minutes=1))
    assert rec["previous_slug"] == "a"
    assert [e["event"] for e in declare.load_events("s1")] == ["declared", "redeclared"]
    assert declare.load_declaration("s1")["slug"] == "b-thread"


def test_declare_validates(env):
    with pytest.raises(ValueError):
        declare.declare("has space", session_id="s1", cwd=str(env.root), branch="b")
    with pytest.raises(ValueError):
        declare.declare("ok", session_id="s1", kind="alien", cwd=str(env.root), branch="b")
    with pytest.raises(ValueError):
        declare.declare("ok", session_id=None, cwd=str(env.root), branch="b")


def test_supersede_and_close(env):
    declare.declare("old", "x", session_id="s1", cwd=str(env.root), branch="b",
                    pane="jarvis-3:@2.%2", now=NOW)
    gone = declare.supersede_pane("jarvis-3:@2.%2", "s2", now=NOW + timedelta(hours=1))
    assert [g["slug"] for g in gone] == ["old"]
    old = declare.load_declaration("s1")
    assert old["superseded_by"] == "s2" and not declare.is_open(old)
    assert declare.previous_in_pane("jarvis-3:@2.%2", "s2")["slug"] == "old"
    # already superseded → not superseded again
    assert declare.supersede_pane("jarvis-3:@2.%2", "s3") == []
    assert declare.mark_closed("s1", "prompt_input_exit", now=NOW + timedelta(hours=2))
    assert declare.load_declaration("s1")["closed_reason"] == "prompt_input_exit"
    assert [e["event"] for e in declare.load_events("s1")] == ["declared", "superseded", "closed"]


def test_note_logs_event_on_session(env):
    note.add_note("t", "parked", status="parked", session_id="s9", cwd=str(env.root), now=NOW)
    evs = declare.load_events("s9")
    assert evs and evs[-1]["event"] == "note" and evs[-1]["slug"] == "t"


# ------------------------------------------------------------------- hooks --

def test_startup_nags_until_declared(env):
    out = _hook("SessionStart", session_id="s1", source="startup", cwd=str(env.root))
    assert "threads declare" in out
    out = _hook("UserPromptSubmit", session_id="s1", prompt="hi")
    assert "Undeclared" in out
    declare.declare("t", "i", session_id="s1", cwd=str(env.root), branch="b", now=NOW)
    assert _hook("UserPromptSubmit", session_id="s1", prompt="hi") == ""
    assert _hook("SessionStart", session_id="s1", source="startup") == ""


def test_startup_auto_declares_from_launcher_env(env, monkeypatch):
    monkeypatch.setenv("THREADS_SLUG", "pool-task")
    monkeypatch.setenv("THREADS_INTENT", "sweep 3")
    monkeypatch.setenv("THREADS_KIND", "cron")
    out = _hook("SessionStart", session_id="s1", source="startup", cwd=str(env.root))
    assert "pool-task" in out and "launcher env" in out
    rec = declare.load_declaration("s1")
    assert rec["kind"] == "cron" and rec["intent"] == "sweep 3"


def test_clear_supersedes_pane_and_names_previous(env):
    _registry(100, "s-old")
    declare.declare("old-thread", "x", session_id="s-old", cwd=str(env.root), branch="b", now=NOW)
    # /clear: same pid + pane, new session id in the registry
    _registry(100, "s-new")
    out = _hook("SessionStart", session_id="s-new", source="clear", cwd=str(env.root))
    assert "old-thread" in out and "threads declare old-thread" in out
    assert declare.load_declaration("s-old")["superseded_by"] == "s-new"
    assert declare.load_declaration("s-new") is None  # the agent still declares
    # a second /clear-start on the same new session is idempotent and quiet about supersession
    out2 = _hook("SessionStart", session_id="s-new", source="clear", cwd=str(env.root))
    assert "old-thread" in out2  # previous_in_pane still names it (history), no double-supersede
    assert sum(1 for e in declare.load_events("s-old") if e["event"] == "superseded") == 1


def test_resume_compact_stop_end_log_events(env):
    declare.declare("t", "i", session_id="s1", cwd=str(env.root), branch="b", now=NOW)
    out = _hook("SessionStart", session_id="s1", source="resume")
    assert "Declared thread: t — i" in out
    assert _hook("SessionStart", session_id="s1", source="compact") == ""
    assert _hook("Stop", session_id="s1", stop_hook_active=False) == ""
    assert _hook("SessionEnd", session_id="s1", reason="logout") == ""
    assert [e["event"] for e in declare.load_events("s1")] == [
        "declared", "resumed", "compacted", "turn_ended", "closed"]
    assert declare.load_declaration("s1")["closed_at"]


def test_hook_fails_open_on_garbage(env):
    out = io.StringIO()
    assert hooks.run(stdin=io.StringIO("not json"), stdout=out) == 0
    assert hooks.run(stdin=io.StringIO('{"hook_event_name":"Nope"}'), stdout=out) == 0
    assert out.getvalue() == ""
    assert main(["hook"]) == 0  # empty stdin through the CLI


# -------------------------------------------------------- sessions integr. --

def test_turn_ended_event_updates_idle_and_slug_labels_row(env):
    _registry(100, "s1")
    old = NOW - timedelta(days=3)
    env.add_transcript(PROJECT, "s1", cwd="/home/x/jarvis", start=old)
    declare.declare("my-thread", "i", session_id="s1", cwd=str(env.root), branch="b", now=old)
    (r,) = sessions.open_sessions(now=NOW, alive={100}.__contains__)
    assert r.label == "my-thread" and r.idle_hours > 48
    _hook("Stop", session_id="s1")  # logged "now" (wall clock) — newer than the transcript
    (r,) = sessions.open_sessions(alive={100}.__contains__)
    assert r.idle_hours < 1 and r.verdict == "recent"


def test_declare_cli_and_show(env, capsys):
    _registry(100, "s1")
    assert main(["declare", "my-thread", "phase", "two", "--session", "s1"]) == 0
    out = capsys.readouterr().out
    assert "declared → my-thread — phase two" in out and "candidate" in out
    assert main(["declare", "--show", "--session", "s1"]) == 0
    assert "my-thread — phase two" in capsys.readouterr().out
    assert main(["declare", "--show", "--session", "nope"]) == 1
    assert main(["declare", "--session", "s1"]) == 2
    assert main(["board"]) == 0
    assert "open sessions" in capsys.readouterr().out
