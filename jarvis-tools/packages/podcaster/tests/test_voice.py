"""The TTS seam: voice resolution, and the offline backend the tests narrate with."""

import wave

import pytest

from podcaster import voice


def test_resolve_finds_a_cached_voice(tmp_path):
    (tmp_path / "en_US-ryan-high.onnx").write_bytes(b"stub")
    assert voice.resolve_voice("en_US-ryan-high", voice_dir=tmp_path).name \
        == "en_US-ryan-high.onnx"


def test_resolve_refuses_to_download_when_told_not_to(tmp_path):
    with pytest.raises(FileNotFoundError, match="download=False"):
        voice.resolve_voice("en_US-nope", voice_dir=tmp_path, download=False)


def test_installed_voices_lists_stems(tmp_path):
    for name in ("b.onnx", "a.onnx", "a.onnx.json"):
        (tmp_path / name).write_bytes(b"x")
    assert voice.installed_voices(tmp_path) == ["a", "b"]
    assert voice.installed_voices(tmp_path / "missing") == []


def test_sine_backend_writes_a_real_wav_scaled_to_the_text(tmp_path):
    backend = voice.SineBackend()
    short = backend.synthesize("hi", tmp_path / "s.wav")
    long = backend.synthesize("hi " * 50, tmp_path / "l.wav")
    with wave.open(str(short)) as wf:
        assert wf.getnframes() > 0 and wf.getnchannels() == 1
    with wave.open(str(long)) as a, wave.open(str(short)) as b:
        assert a.getnframes() > b.getnframes()


def test_piper_backend_defers_its_import_until_used():
    backend = voice.PiperBackend(voice="en_US-ryan-high")
    assert backend.name == "en_US-ryan-high"          # no onnxruntime needed yet
    assert backend.length_scale == voice.DEFAULT_LENGTH_SCALE
