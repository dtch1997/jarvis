"""Slack adapter: the Daniel-only filter, dedup + thread descent, audio detect."""

from __future__ import annotations

from mailroom import slack

from mailroom_testkit import CH, DAN, BOT, FakeSlack, slack_msg


def test_is_daniel_filters_bot_and_others():
    assert slack.is_daniel(slack_msg("1", user=DAN))
    # the bot's own posts (gazette/desk/flare via the same app) carry bot_id
    assert not slack.is_daniel(slack_msg("2", user=BOT, bot_id="B1"))
    assert not slack.is_daniel(slack_msg("3", user=DAN, bot_id="B1"))  # any bot_id
    assert not slack.is_daniel(slack_msg("4", user="U_OTHER"))
    assert not slack.is_daniel(slack_msg("5", user=DAN, subtype="channel_join"))


def test_collect_captures_dedup_and_threads():
    top = [
        slack_msg("100", text="top level thought", reply_count=1),
        slack_msg("90", user=BOT, bot_id="B1", text="bot noise"),
        slack_msg("80", text="another"),
    ]
    replies = {"100": [
        slack_msg("100", text="top level thought", reply_count=1),  # parent echoes in replies
        slack_msg("101", text="daniel reply in thread", thread_ts="100"),
        slack_msg("102", user="U_OTHER", text="someone else"),
    ]}
    caps = slack.collect_captures(FakeSlack(top, replies), CH, oldest="0")
    texts = [c.text for c in caps]
    assert "top level thought" in texts
    assert "daniel reply in thread" in texts
    assert "another" in texts
    assert "bot noise" not in texts
    assert "someone else" not in texts
    # sorted oldest-first, no dup of the parent
    assert [c.ts for c in caps] == ["80", "100", "101"]


def test_audio_capture_detected():
    files = [{"mimetype": "audio/mp4", "name": "clip.m4a",
              "url_private_download": "http://x", "id": "F1"}]
    cap = slack.to_capture(slack_msg("100", text="", files=files), CH)
    assert cap.is_audio
    assert cap.id == f"slack-{CH}-100"


def test_empty_message_no_content():
    cap = slack.to_capture(slack_msg("100", text="   "), CH)
    assert not cap.has_content
