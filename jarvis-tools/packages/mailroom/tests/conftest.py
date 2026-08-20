"""Fixtures: a scratch spool, fake Slack/Todoist clients, a canned triage
runner, and a fake transcriber. No network, no real ``claude``, no real home —
every path is redirected under ``tmp_path`` via env overrides.
"""

from __future__ import annotations

import json

import pytest

from mailroom_testkit import NOW, Env  # noqa: F401 (re-exported for tests)


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    goals = tmp_path / "goals"
    memory = tmp_path / "jarvis-memory"
    for d in (goals, memory):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MAILROOM_HOME", str(tmp_path / "mailroomhome"))
    monkeypatch.setenv("MAILROOM_GOALS_DIR", str(goals))
    monkeypatch.setenv("MAILROOM_MEMORY_DIR", str(memory))
    # never let a test's default GoalLander touch the real deployed checkout —
    # point it at a non-repo so it fails soft (tests that want the PR vehicle
    # build their own fixture repo and pass goal_lander explicitly)
    monkeypatch.setenv("MAILROOM_GOALS_REPO", str(tmp_path / "not-a-repo"))
    monkeypatch.setenv("FLARE_HOME", str(tmp_path / "flarehome"))
    monkeypatch.delenv("FLARE_WEBHOOK", raising=False)
    return Env(tmp_path, goals, memory)


# --------------------------------------------------------------------------- #
# triage runner + transcriber
# --------------------------------------------------------------------------- #
@pytest.fixture
def triage_runner():
    """A triage runner that parses ids+text from the real prompt and classifies
    by keyword (first match): 'urgent'→urgent todo, 'paper'→paper, 'goal:'→
    goal-signal, 'note:'→thread-note, 'idea'→research-idea, 'admin'→admin,
    'todo'/'buy'→todo, else unclear."""
    import re
    calls = {"n": 0}

    def classify(raw):
        raw = raw.lower()
        if "urgent" in raw:
            return {"type": "todo", "project": "Focus Areas", "urgency": "high"}
        if "paper" in raw:
            return {"type": "paper", "arxiv_id": "2401.00001"}
        if "goal:" in raw:
            return {"type": "goal-signal", "goal": "phd-thesis"}
        if "note:" in raw:
            return {"type": "thread-note", "candidate_slugs": ["my-thread"]}
        if "idea" in raw:
            return {"type": "research-idea"}
        if "admin" in raw:
            return {"type": "admin", "project": "Automation"}
        if "todo" in raw or "buy" in raw:
            return {"type": "todo", "project": "Focus Areas"}
        return {"type": "unclear"}

    def runner(prompt, *, model):
        calls["n"] += 1
        results = []
        for m in re.finditer(r"- id: (\S+)\n  source: [^\n]*\n  text: ([^\n]*)", prompt):
            tid, raw = m.group(1), m.group(2)
            obj = {"id": tid, "title": raw[:40]}
            obj.update(classify(raw))
            results.append(obj)
        return {"text": json.dumps({"results": results}), "cost_usd": 0.001}

    runner.calls = calls
    return runner


@pytest.fixture
def fake_transcriber():
    def t(wav_path):
        return "transcribed words here"
    return t


@pytest.fixture
def note_calls():
    calls = []

    def runner(slug, body, *, status=None):
        calls.append((slug, status, body))
        return "noted"

    runner.calls = calls
    return runner
