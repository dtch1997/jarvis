"""sessions: the deterministic open-sessions view (offline, no model)."""

from __future__ import annotations

import json
import os
from datetime import timedelta

from threads import config, note, sessions
from threads.cli import main

from conftest import NOW

PROJECT = "-home-x-jarvis"


def _registry(env, pid: int, sid: str, *, status="idle", status_at=None,
              name="jarvis-os-ab", name_source="derived", tmux="jarvis-3:@2.%2"):
    d = config.Path(os.environ["THREADS_CLAUDE_SESSIONS_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    at = status_at or (NOW - timedelta(hours=1))
    (d / f"{pid}.json").write_text(json.dumps({
        "pid": pid, "sessionId": sid, "cwd": "/home/x/jarvis",
        "startedAt": int((NOW - timedelta(days=3)).timestamp() * 1000),
        "kind": "interactive", "tmux": tmux, "name": name,
        "nameSource": name_source, "status": status,
        "statusUpdatedAt": int(at.timestamp() * 1000),
    }))
    (d / f"{pid}.deadbeef.key").write_text("{}")  # sibling key files are ignored


def _flags(sid: str, flags, topic="t"):
    d = config.Path(os.environ["THREADS_STATUSLINE_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps({"topic": topic, "flags": flags}))


def _pr_link(env, sid: str, url: str):
    p = env.projects / PROJECT / f"{sid}.jsonl"
    with open(p, "a") as f:
        f.write(json.dumps({"type": "pr-link", "sessionId": sid, "prUrl": url,
                            "timestamp": NOW.isoformat()}) + "\n")


def _artifact_publish(env, sid: str, when):
    p = env.projects / PROJECT / f"{sid}.jsonl"
    with open(p, "a") as f:
        f.write(json.dumps({
            "type": "assistant", "sessionId": sid, "timestamp": when.isoformat(),
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Artifact", "id": "a1",
                 "input": {"file_path": "/tmp/x.html", "favicon": "x"}}]},
        }) + "\n")


def _declare(sid: str, slug: str, intent="doing x"):
    d = config.declarations_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps({"slug": slug, "intent": intent,
                                               "kind": "interactive"}))


ALIVE = {100, 101, 102, 103, 104, 105}
alive = ALIVE.__contains__
OLD = NOW - timedelta(days=3)


def test_busy_and_recent_are_left_alone(env):
    _registry(env, 100, "s-busy", status="busy")
    env.add_transcript(PROJECT, "s-busy", cwd="/home/x/jarvis", start=OLD)
    _registry(env, 101, "s-recent")
    env.add_transcript(PROJECT, "s-recent", cwd="/home/x/jarvis",
                       start=NOW - timedelta(hours=2))
    rows = {r.session_id: r for r in sessions.open_sessions(now=NOW, alive=alive)}
    assert rows["s-busy"].verdict == "busy"
    assert rows["s-recent"].verdict == "recent"
    assert rows["s-recent"].idle_hours < 12


def test_flags_force_needs_park(env):
    _registry(env, 100, "s-flag")
    env.add_transcript(PROJECT, "s-flag", cwd="/home/x/jarvis", start=OLD)
    _flags("s-flag", ["open PR for branch x"])
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.verdict == "needs-park"
    assert "1 open flag" in r.reason
    assert r.idle_hours > 24 * 2


def test_pr_without_later_note_needs_park_then_note_makes_closable(env):
    _registry(env, 100, "s-pr")
    env.add_transcript(PROJECT, "s-pr", cwd="/home/x/jarvis", start=OLD)
    _pr_link(env, "s-pr", "https://github.com/o/r/pull/7")
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.verdict == "needs-park"
    assert r.prs == ["https://github.com/o/r/pull/7"]
    # a note newer than the last turn, naming the session, discharges it
    note.add_note("some-thread", "parked", status="parked", session_id="s-pr",
                  cwd=str(env.root), now=OLD + timedelta(hours=1))
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.verdict == "closable"
    assert r.note_slug == "some-thread"
    assert r.last_note_status == "parked"


def test_artifact_publish_counts_as_obligation(env):
    _registry(env, 100, "s-art")
    env.add_transcript(PROJECT, "s-art", cwd="/home/x/jarvis", start=OLD)
    _artifact_publish(env, "s-art", OLD + timedelta(minutes=5))
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.verdict == "needs-park"
    assert r.artifacts == 1


def test_declared_slug_note_discharges_and_labels(env):
    _registry(env, 100, "s-decl")
    env.add_transcript(PROJECT, "s-decl", cwd="/home/x/jarvis", start=OLD)
    _pr_link(env, "s-decl", "https://github.com/o/r/pull/8")
    _declare("s-decl", "my-thread", intent="phase 2")
    # note on the declared slug, no session_id — still counts
    note.add_note("my-thread", "parked here", status="parked",
                  cwd=str(env.root), now=OLD + timedelta(hours=2))
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.declared and r.slug == "my-thread" and r.label == "my-thread"
    assert r.verdict == "closable"


def test_nothing_owed_is_closable_and_undeclared_is_marked(env):
    _registry(env, 100, "s-empty")
    env.add_transcript(PROJECT, "s-empty", cwd="/home/x/jarvis", start=OLD)
    (r,) = sessions.open_sessions(now=NOW, alive=alive)
    assert r.verdict == "closable"
    assert not r.declared
    text = sessions.render([r], now=NOW)
    assert "(undeclared)" in text and "closable" in text


def test_dead_pid_hidden_unless_all_and_self_excluded(env, monkeypatch):
    _registry(env, 999, "s-dead")
    _registry(env, 100, "s-me")
    _registry(env, 101, "s-other")
    for sid in ("s-dead", "s-me", "s-other"):
        env.add_transcript(PROJECT, sid, cwd="/home/x/jarvis", start=OLD)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s-me")
    ids = [r.session_id for r in sessions.open_sessions(now=NOW, alive=alive)]
    assert ids == ["s-other"]
    ids = {r.session_id for r in sessions.open_sessions(now=NOW, alive=alive,
                                                        include_gone=True,
                                                        include_self=True)}
    assert ids == {"s-dead", "s-me", "s-other"}
    gone = [r for r in sessions.open_sessions(now=NOW, alive=alive, include_gone=True)
            if r.session_id == "s-dead"]
    assert gone[0].verdict == "gone"


def test_last_turn_ignores_tool_results_and_mtime(env):
    _registry(env, 100, "s-turn")
    p = env.add_transcript(PROJECT, "s-turn", cwd="/home/x/jarvis", start=OLD,
                           mtime=NOW)  # touched "now", but the last turn is old
    with open(p, "a") as f:  # a trailing tool-result-only user line is not a turn
        f.write(json.dumps({"type": "user", "timestamp": NOW.isoformat(),
                            "message": {"role": "user", "content": [
                                {"type": "tool_result", "tool_use_id": "t"}]}}) + "\n")
    facts = sessions.scan_transcript(p)
    assert facts.last_turn < NOW - timedelta(days=2)
    assert facts.n_user_turns == 8
    assert facts.last_user.startswith("user turn 7")


def test_cli_text_and_json(env, capsys):
    _registry(env, 100, "s-cli", name="Poisoned chalice", name_source="user")
    env.add_transcript(PROJECT, "s-cli", cwd="/home/x/jarvis", start=OLD)
    sessions._pid_alive = alive  # the CLI uses the real liveness probe
    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "Poisoned chalice" in out and "open sessions" in out
    assert main(["sessions", "--json", "--idle-hours", "1"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["session_id"] == "s-cli" and rows[0]["verdict"] == "closable"
