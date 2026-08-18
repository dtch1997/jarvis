"""ingest: record creation, idempotency, reactions, voice leg, ingest_check."""

from __future__ import annotations

from mailroom import ingest, spool

from mailroom_testkit import CH, NOW, FakeSlack, FakeTodoist, slack_msg


def _todoist_task(tid, content, project=None):
    from mailroom import config
    return {"id": tid, "content": content, "project_id": config.TODOIST_INBOX_ID,
            "created_at": "2026-06-01T00:00:00Z", "labels": []}


def test_ingest_creates_records_and_reacts(env, fake_transcriber):
    slack = FakeSlack([slack_msg("100", text="a thought"),
                       slack_msg("90", text="older")])
    td = FakeTodoist(inbox=[_todoist_task("t1", "buy milk")])
    res = ingest.ingest(backfill=True, client=slack, todoist_client=td,
                        transcriber=fake_transcriber, now=NOW)
    assert res.slack_new == 2
    assert res.todoist_new == 1
    assert res.reactions == 2
    rec = spool.load_thought(f"slack-{CH}-100")
    assert rec["source"] == "slack"
    assert rec["backfill"] is True
    assert rec["reacted"] is True
    assert spool.load_thought("todoist-t1")["source"] == "todoist"


def test_ingest_idempotent_rerun_no_new(env, fake_transcriber):
    slack = FakeSlack([slack_msg("100", text="a thought")])
    td = FakeTodoist(inbox=[_todoist_task("t1", "buy milk")])
    ingest.ingest(backfill=True, client=slack, todoist_client=td,
                  transcriber=fake_transcriber, now=NOW)
    res2 = ingest.ingest(client=slack, todoist_client=td,
                         transcriber=fake_transcriber, now=NOW)
    assert res2.slack_new == 0
    assert res2.slack_skipped == 1
    assert res2.todoist_new == 0
    assert res2.todoist_skipped == 1


def test_voice_leg_transcribes_and_stores_pointer(env, fake_transcriber, monkeypatch):
    # avoid ffmpeg/rclone: stub the whole voice.process_audio
    from mailroom import voice
    monkeypatch.setattr(voice, "process_audio", lambda local, tid, **k: voice.VoiceResult(
        transcript="hello from parakeet",
        gcs_pointer="gcs:bucket/audio/x.m4a", local_path=str(local),
        slack_transcription="slack said hi", duration_ms=7000))
    files = [{"mimetype": "audio/mp4", "name": "clip.m4a",
              "url_private_download": "http://x", "id": "F1", "filetype": "m4a"}]
    slack = FakeSlack([slack_msg("100", text="", files=files)])
    res = ingest.ingest(backfill=True, client=slack, todoist_client=FakeTodoist(),
                        transcriber=fake_transcriber, now=NOW)
    assert res.voice_transcribed == 1
    rec = spool.load_thought(f"slack-{CH}-100")
    assert rec["source"] == "voice"
    assert rec["raw"] == "hello from parakeet"
    assert rec["audio"]["gs"] == "gcs:bucket/audio/x.m4a"
    assert rec["audio"]["slack_transcription"] == "slack said hi"


def test_ingest_check_passes_when_covered(env, fake_transcriber):
    slack = FakeSlack([slack_msg("100", text="a thought")])
    td = FakeTodoist(inbox=[_todoist_task("t1", "buy milk")])
    ingest.ingest(backfill=True, client=slack, todoist_client=td,
                  transcriber=fake_transcriber, now=NOW)
    ok, report = ingest.ingest_check(client=slack, todoist_client=td, now=NOW)
    assert ok, report


def test_ingest_check_fails_on_new_uningested(env, fake_transcriber):
    slack = FakeSlack([slack_msg("100", text="a thought")])
    td = FakeTodoist(inbox=[])
    ingest.ingest(backfill=True, client=slack, todoist_client=td,
                  transcriber=fake_transcriber, now=NOW)
    # a new Daniel message appears after ingest
    slack.messages.append(slack_msg("200", text="brand new"))
    ok, report = ingest.ingest_check(client=slack, todoist_client=td, now=NOW)
    assert not ok
    assert "un-ingested" in report


def test_ingest_check_fails_before_any_run(env):
    ok, report = ingest.ingest_check(client=FakeSlack(), todoist_client=FakeTodoist(), now=NOW)
    assert not ok
    assert "no ingest" in report
