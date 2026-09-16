"""Mastering: joining chunks with the pause structure, and the MP3 hand-off."""

import wave

import pytest

from podcaster import audio
from podcaster.voice import SineBackend

from podcaster_testkit import RecordingFfmpeg


def _wav(tmp_path, name, text="hello there"):
    return SineBackend().synthesize(text, tmp_path / name)


def test_concat_adds_the_requested_gaps(tmp_path):
    a, b = _wav(tmp_path, "a.wav"), _wav(tmp_path, "b.wav")
    solo = audio.wav_duration(a) + audio.wav_duration(b)
    out = audio.concat_wavs([(a, 0.5), (b, 0.0)], tmp_path / "out.wav")
    assert audio.wav_duration(out) == pytest.approx(solo + 0.5, abs=0.01)


def test_concat_preserves_the_source_format(tmp_path):
    out = audio.concat_wavs([(_wav(tmp_path, "a.wav"), 0.0)], tmp_path / "o.wav")
    with wave.open(str(out)) as wf:
        assert (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) == (1, 2, 22050)


def test_concat_refuses_mismatched_formats(tmp_path):
    a = _wav(tmp_path, "a.wav")
    b = SineBackend(sample_rate=8000).synthesize("hello there", tmp_path / "b.wav")
    with pytest.raises(ValueError, match="format mismatch"):
        audio.concat_wavs([(a, 0.0), (b, 0.0)], tmp_path / "o.wav")


def test_concat_of_nothing_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        audio.concat_wavs([], tmp_path / "o.wav")


def test_mp3_call_carries_mono_bitrate_and_id3_tags(tmp_path):
    ff = RecordingFfmpeg()
    mp3 = audio.to_mp3(_wav(tmp_path, "a.wav"), tmp_path / "ep.mp3",
                       title="The Agreement Trap", album="jarvis podcaster",
                       comment="notes", runner=ff)
    argv = " ".join(ff.calls[0])
    assert "-ac 1" in argv and audio.MP3_BITRATE in argv
    assert "title=The Agreement Trap" in argv and "comment=notes" in argv
    assert argv.endswith(str(mp3)) and mp3.exists()


def test_empty_metadata_is_not_passed_to_ffmpeg(tmp_path):
    ff = RecordingFfmpeg()
    audio.to_mp3(_wav(tmp_path, "a.wav"), tmp_path / "ep.mp3", title="t", runner=ff)
    assert "comment=" not in " ".join(ff.calls[0])
