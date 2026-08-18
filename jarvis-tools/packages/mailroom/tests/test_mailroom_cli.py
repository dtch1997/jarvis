"""cli: --check exit codes and command dispatch (no network, no model)."""

from __future__ import annotations

import pytest

from mailroom import ingest, route, spool
from mailroom.cli import main

from mailroom_testkit import CH, NOW, FakeSlack, FakeTodoist, slack_msg


@pytest.fixture
def routed_spool(env, triage_runner, note_calls, monkeypatch):
    """A fully ingested + routed spool, with the live clients stubbed out so the
    bare CLI (which constructs real clients) never hits the network."""
    slack = FakeSlack([slack_msg("100", text="note: a thing"),
                       slack_msg("101", text="todo: another")])
    td = FakeTodoist()
    ingest.ingest(backfill=True, client=slack, todoist_client=td,
                  transcriber=lambda w: "x", now=NOW)
    route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                note_runner=note_calls, now=NOW)
    return env


def test_route_check_exit_0_after_route(routed_spool, capsys):
    assert main(["route", "--check"]) == 0
    assert "OK" in capsys.readouterr().out


def test_route_check_exit_1_before_route(env, capsys):
    assert main(["route", "--check"]) == 1


def test_render_prints_digest(routed_spool, capsys):
    assert main(["render", "--no-stale"]) == 0
    out = capsys.readouterr().out
    assert "mailroom digest" in out
    assert "Routes" in out


def test_status_prints_summary(routed_spool, capsys):
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "mailroom:" in out
    assert "route --check" in out


def test_ingest_check_exit_1_before_ingest(env, monkeypatch, capsys):
    # stub the real clients so --check doesn't try the network
    from mailroom import slack as slack_mod, todoist as todoist_mod
    monkeypatch.setattr(slack_mod, "SlackClient", lambda *a, **k: FakeSlack([]))
    monkeypatch.setattr(todoist_mod, "TodoistClient", lambda *a, **k: FakeTodoist())
    assert main(["ingest", "--check"]) == 1
