"""digest: markdown counts, drain line, headline, stale sweep."""

from __future__ import annotations

from mailroom import config, digest, ingest, route

from mailroom_testkit import NOW, FakeSlack, FakeTodoist, slack_msg


def _prep(env, triage_runner, note_calls, td=None):
    slack = FakeSlack([slack_msg("100", text="note: a thing"),
                       slack_msg("101", text="mmm")])
    td = td or FakeTodoist()
    ingest.ingest(backfill=True, client=slack, todoist_client=td,
                  transcriber=lambda w: "x", now=NOW)
    route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                note_runner=note_calls, now=NOW)


def test_render_markdown_has_counts_and_drain(env, triage_runner, note_calls):
    _prep(env, triage_runner, note_calls)
    md = digest.render_markdown(now=NOW)
    assert "**2** thought(s)" in md
    assert "completions 0" in md
    assert "## Routes" in md
    assert "## Unclear" in md


def test_headline(env, triage_runner, note_calls):
    _prep(env, triage_runner, note_calls)
    hl = digest.digest_headline(now=NOW)
    assert "mailroom:" in hl
    assert "routed" in hl


def test_nonempty_day_and_flare(env, triage_runner, note_calls, monkeypatch):
    import flare
    sent = []
    monkeypatch.setattr(flare, "send", lambda *a, **k: sent.append((a, k)))
    assert digest.is_nonempty_day(now=NOW) is False  # empty spool
    _prep(env, triage_runner, note_calls)
    assert digest.is_nonempty_day(now=NOW) is True
    assert digest.flare_headline(now=NOW) is True
    assert sent and sent[0][1].get("sev") == "info"


def test_stale_candidates(env):
    class TD:
        def tasks(self, pid):
            if pid == config.TODOIST_PROJECTS["Writing"]:
                return [{"id": "x", "content": "old draft",
                         "added_at": "2026-01-01T00:00:00Z"}]
            return []
    stale = digest.stale_candidates(TD(), stale_days=60, now=NOW)
    assert stale and stale[0]["project"] == "Writing"
    assert stale[0]["days"] > 60
