"""voice: GCS mirror pointer + Slack cross-check extraction (no ffmpeg/onnx)."""

from __future__ import annotations

from pathlib import Path

from mailroom import config, voice


def test_mirror_to_gcs_pointer(tmp_path):
    local = tmp_path / "clip.m4a"
    local.write_bytes(b"x")
    calls = []
    ptr = voice.mirror_to_gcs(local, "slack-C-100", runner=lambda a: calls.append(a))
    assert ptr == f"{config.GCS_AUDIO_PREFIX}/slack-C-100.m4a"
    assert calls and calls[0][0] == "rclone"


def test_mirror_to_gcs_survives_failure(tmp_path):
    local = tmp_path / "clip.m4a"
    local.write_bytes(b"x")

    def boom(a):
        raise RuntimeError("rclone down")

    ptr = voice.mirror_to_gcs(local, "id1", runner=boom)
    assert ptr.endswith("id1.m4a")  # pointer still returned


def test_slack_transcription_text():
    f = {"transcription": {"status": "complete",
                           "preview": {"content": "hi there"}}}
    assert voice.slack_transcription_text(f) == "hi there"
    assert voice.slack_transcription_text({"transcription": {"status": "processing"}}) == ""
    assert voice.slack_transcription_text({}) == ""


def test_process_audio_seams(tmp_path, monkeypatch):
    local = tmp_path / "clip.m4a"
    local.write_bytes(b"x")
    monkeypatch.setattr(voice, "transcode_16k_mono", lambda s, d: Path(d).write_bytes(b"w"))
    res = voice.process_audio(local, "id1", transcriber=lambda w: "the words",
                              gcs_runner=lambda a: None, duration_ms=5000)
    assert res.transcript == "the words"
    assert res.duration_ms == 5000
    assert res.gcs_pointer.endswith("id1.m4a")
