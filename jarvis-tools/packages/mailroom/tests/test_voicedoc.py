"""voicedoc: clip → cleanup → Drive upload → draft, all through seams."""

from __future__ import annotations

import json

import pytest

from mailroom import config, spool, voice, voicedoc
from mailroom_testkit import CH, FakeSlack, slack_msg

AUDIO = {"mimetype": "audio/mp4", "filetype": "m4a",
         "url_private_download": "https://files.example/clip", "duration_ms": 4000}

CLEANUP_REPLY = {"title": "Reward hacking as a market",
                 "html": "<p>The core idea is X.</p>",
                 "tldr": "Two sentences of summary. Here is the second."}


@pytest.fixture(autouse=True)
def _spool():
    config.ensure_spool()


@pytest.fixture(autouse=True)
def _no_ffmpeg(monkeypatch):
    monkeypatch.setattr(voice, "transcode_16k_mono",
                        lambda s, d: d.write_bytes(b"wav"))


@pytest.fixture
def cleanup_runner():
    def runner(prompt, *, model):
        runner.prompts.append(prompt)
        return {"text": json.dumps(CLEANUP_REPLY), "cost_usd": 0.01}
    runner.prompts = []
    return runner


class FakeRclone:
    """Records argv; serves an lsf listing that contains the uploaded doc."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, argv):
        self.calls.append(argv)
        if self.fail and argv[1] == "copyto":
            raise RuntimeError("rclone: couldn't connect")
        if argv[1] == "lsf":
            uploaded = [a for a in self.calls if a[1] == "copyto"]
            name = uploaded[-1][3].rsplit("/", 1)[-1] if uploaded else ""

            class P:
                stdout = f"{name};DOCID123\nother.txt;ZZZ\n"
            return P()
        return None


def _set_cursor(channel=CH, ts="100"):
    spool.update_state(**{voicedoc._cursor_key(channel): ts})


def test_parse_cleanup_lenient():
    assert voicedoc.parse_cleanup(json.dumps(CLEANUP_REPLY))["title"] == CLEANUP_REPLY["title"]
    fenced = "```json\n" + json.dumps(CLEANUP_REPLY) + "\n```"
    assert voicedoc.parse_cleanup(fenced)["html"] == CLEANUP_REPLY["html"]
    assert voicedoc.parse_cleanup("not json") is None
    assert voicedoc.parse_cleanup(json.dumps({"title": "t", "html": ""})) is None


def test_render_html_escapes_title():
    page = voicedoc.render_html("A <b>title</b>", "<p>x</p>", date="2026-09-05")
    assert "A &lt;b&gt;title&lt;/b&gt;" in page
    assert "<p>x</p>" in page and "voice note (2026-09-05)" in page


def test_upload_gdoc_url_and_import_flag():
    rc = FakeRclone()
    url = voicedoc.upload_gdoc("<html></html>", "My Doc", remote="work:",
                               folder="model motivations", date="2026-09-05", run=rc)
    assert url == "https://docs.google.com/document/d/DOCID123/edit"
    copyto = rc.calls[0]
    assert copyto[1] == "copyto"
    assert copyto[3] == "work:model motivations/2026-09-05 My Doc.html"
    assert "--drive-import-formats" in copyto


def test_first_run_initializes_cursor_without_backfill(cleanup_runner):
    client = FakeSlack(messages=[slack_msg("50.000000", files=[AUDIO])])
    recs = voicedoc.run_once(client=client, transcriber=lambda w: "words",
                             runner=cleanup_runner, rclone_run=FakeRclone(),
                             gcs_runner=lambda a: None, now=100.0)
    assert recs == []  # old clip not docified
    assert spool.load_state()[voicedoc._cursor_key(CH)] == "100.000000"


def test_clip_end_to_end(cleanup_runner):
    _set_cursor()
    client = FakeSlack(
        messages=[slack_msg("101.000000", text="make it a proposal", files=[AUDIO])])
    recs = voicedoc.run_once(client=client, transcriber=lambda w: "raw words",
                             runner=cleanup_runner, rclone_run=FakeRclone(),
                             gcs_runner=lambda a: None)
    assert len(recs) == 1 and "error" not in recs[0]
    assert recs[0]["doc_url"].startswith("https://docs.google.com/document/d/")
    # steering text made it into the prompt
    assert "make it a proposal" in cleanup_runner.prompts[0]
    # draft posted top-level: title, tldr, url
    ch, thread, text = client.posts[-1]
    assert ch == CH and thread is None
    assert CLEANUP_REPLY["title"] in text and recs[0]["doc_url"] in text
    assert (CH, "101.000000", "page_facing_up") in client.reactions
    # cursor advanced; a second pass is a no-op
    assert spool.load_state()[voicedoc._cursor_key(CH)] == "101.000000"
    assert voicedoc.run_once(client=client, transcriber=lambda w: "x",
                             runner=cleanup_runner, rclone_run=FakeRclone(),
                             gcs_runner=lambda a: None) == []


def test_text_only_messages_skipped_but_cursor_advances(cleanup_runner):
    _set_cursor()
    client = FakeSlack(messages=[slack_msg("102.000000", text="just a thought")])
    recs = voicedoc.run_once(client=client, runner=cleanup_runner,
                             rclone_run=FakeRclone(), gcs_runner=lambda a: None)
    assert recs == [] and client.posts == []
    assert spool.load_state()[voicedoc._cursor_key(CH)] == "102.000000"


def test_failure_replies_in_thread_and_advances(cleanup_runner):
    _set_cursor()
    client = FakeSlack(messages=[slack_msg("103.000000", files=[AUDIO])])
    recs = voicedoc.run_once(client=client, transcriber=lambda w: "words",
                             runner=cleanup_runner, rclone_run=FakeRclone(fail=True),
                             gcs_runner=lambda a: None)
    assert len(recs) == 1 and "couldn't connect" in recs[0]["error"]
    ch, thread, text = client.posts[-1]
    assert thread == "103.000000" and "voicedoc failed" in text
    assert (CH, "103.000000", "warning") in client.reactions
    assert spool.load_state()[voicedoc._cursor_key(CH)] == "103.000000"


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME", str(tmp_path / "vh"))
    config.ensure_spool()
    vd = config.load_config().voicedoc
    assert vd.enabled and vd.drive_remote == "gdrive-work:"
    # edit a knob and reload
    p = config.config_path()
    p.write_text(p.read_text().replace('drive_folder = ""',
                                       'drive_folder = "model motivations"'))
    assert config.load_config().voicedoc.drive_folder == "model motivations"


def test_ensure_spool_appends_voicedoc_to_legacy_config(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME", str(tmp_path / "vh2"))
    config.mailroom_dir().mkdir(parents=True)
    config.config_path().write_text('channels = ["CX"]\n')
    config.ensure_spool()
    text = config.config_path().read_text()
    assert text.startswith('channels = ["CX"]')
    assert "[voicedoc]" in text
    cfg = config.load_config()
    assert cfg.channels == ["CX"] and cfg.voicedoc.enabled
