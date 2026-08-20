"""The whole flow, offline: fake model, fake ffmpeg, tone-generator voice.

These run the real graph — fan-outs, retries, gate, chunking, wav concatenation,
mastering — so a regression in the pipeline's wiring fails here rather than in a
live run that costs money and twenty minutes.
"""

import asyncio
import json

import pytest

from podcaster import audio
from podcaster.models import Episode, read_json, Script, Brief
from podcaster.pipeline import EpisodeSpec, make_episode, narrate_script
from podcaster.voice import SineBackend

from podcaster_testkit import FakeRunner, RecordingFfmpeg, RecordingRclone


def _spec(**kw) -> EpisodeSpec:
    base = dict(topic="training cooperativeness", target_minutes=4.0, n_questions=3,
                beats=3, today="2026-08-19")
    return EpisodeSpec(**{**base, **kw})


def _run(spec, tmp_path, *, runner=None, ffmpeg=None, **kw) -> Episode:
    monkeyed = ffmpeg or RecordingFfmpeg()
    real_to_mp3 = audio.to_mp3
    try:
        audio.to_mp3 = lambda *a, **k: real_to_mp3(*a, **{**k, "runner": monkeyed})
        return asyncio.run(make_episode(
            spec, out_dir=tmp_path / "episodes",
            runner=runner or FakeRunner(questions=spec.n_questions,
                                        target_minutes=spec.target_minutes),
            tts=SineBackend(), **kw))
    finally:
        audio.to_mp3 = real_to_mp3


def test_end_to_end_produces_an_mp3_and_its_provenance(tmp_path):
    spec = _spec()
    episode = _run(spec, tmp_path)
    assert episode.mp3_path.endswith(".mp3")
    assert episode.duration_s > 0 and episode.words > 0
    assert episode.voice == "sine"
    out = tmp_path / "episodes"
    slug = spec.episode_slug()
    assert slug.startswith("2026-08-19-training-cooperativeness")
    for suffix in ("brief.json", "script.json", "episode.json"):
        assert (out / f"{slug}.{suffix}").exists()
    assert read_json(Episode, out / f"{slug}.episode.json") == episode
    brief = read_json(Brief, out / f"{slug}.brief.json")
    assert len(brief.findings) == 6                     # 3 questions x 2 findings
    assert brief.sources


def test_the_audio_is_assembled_from_every_segment_with_breaths(tmp_path):
    episode = _run(_spec(), tmp_path)
    script = read_json(Script, episode.script_path)
    chunks = sorted((tmp_path / "episodes" / "chunks").glob("*.segment*.wav"))
    assert len(chunks) == len(script.segments)
    solo = sum(audio.wav_duration(p) for p in chunks)
    assert episode.duration_s == pytest.approx(
        solo + audio.SEGMENT_GAP_S * (len(chunks) - 1), abs=0.05)


def test_a_draft_that_fails_the_style_gate_is_rewritten_with_the_complaints(tmp_path):
    runner = FakeRunner(questions=2, target_minutes=4.0, bad_first_draft=True)
    episode = _run(_spec(n_questions=2), tmp_path, runner=runner)
    assert runner.calls["script"] == 2                  # first draft was rejected
    rewrite = [p for p in runner.prompts if "failed the listenability gate" in p]
    assert rewrite and "bullet" in rewrite[-1]
    assert episode.duration_s > 0


def test_an_empty_research_question_is_retried(tmp_path):
    runner = FakeRunner(questions=2, target_minutes=4.0, empty_first_dig=True)
    _run(_spec(n_questions=2), tmp_path, runner=runner)
    assert runner.calls["dig"] == 3                     # 2 questions + 1 retry


def test_publishing_pushes_the_mp3_and_records_the_pointer(tmp_path):
    rclone = RecordingRclone()
    episode = _run(_spec(), tmp_path, publish_prefix="gcs:bucket/prefix",
                   publish_runner=rclone)
    assert episode.pointer == f"gcs:bucket/prefix/{_spec().episode_slug()}.mp3"
    pushed = [c[-1] for c in rclone.calls]
    assert any(p.endswith(".mp3") for p in pushed)
    assert any(p.endswith(".script.json") for p in pushed)
    assert episode.pointer in read_json(
        Episode, tmp_path / "episodes" / f"{_spec().episode_slug()}.episode.json").pointer


def test_the_flow_records_a_manifest_for_reproducibility(tmp_path):
    spec = _spec()
    _run(spec, tmp_path)
    manifest = json.loads((tmp_path / "episodes" / "runs" / "manifest.json").read_text())
    assert manifest["config"]["topic"] == spec.topic
    assert manifest["config"]["target_minutes"] == spec.target_minutes
    assert "git" in manifest


def test_a_narration_failure_fails_the_episode_rather_than_leaving_a_hole(tmp_path):
    class BrokenVoice:
        name = "broken"
        calls = 0

        def synthesize(self, text, path):
            BrokenVoice.calls += 1
            raise RuntimeError("onnx exploded")

    with pytest.raises(RuntimeError):
        asyncio.run(make_episode(
            _spec(n_questions=2), out_dir=tmp_path / "episodes",
            runner=FakeRunner(questions=2, target_minutes=4.0), tts=BrokenVoice()))
    assert BrokenVoice.calls >= 2                        # retried before giving up


def test_slug_is_overridable_and_filesystem_safe():
    assert _spec(topic="RLHF: what now?").episode_slug() == "2026-08-19-rlhf-what-now"
    assert _spec(slug="my-episode").episode_slug() == "my-episode"


def test_narrate_script_path_needs_no_model_calls(tmp_path):
    script = Script(topic="t", title="Solo Narration", blurb="notes",
                    target_minutes=1.0, segments=[
                        {"kind": "cold_open", "title": "a", "text": "You are here. It is fine."},
                        {"kind": "beat", "title": "b", "text": "Two sentences. Both short."},
                        {"kind": "sign_off", "title": "c", "text": "That is all. Talk soon."}])
    script = Script.from_dict(json.loads(json.dumps(script.__dict__, default=lambda o: o.__dict__)))
    ff = RecordingFfmpeg()
    real_to_mp3 = audio.to_mp3
    try:
        audio.to_mp3 = lambda *a, **k: real_to_mp3(*a, **{**k, "runner": ff})
        episode = narrate_script(script, out_dir=tmp_path / "eps", tts=SineBackend())
    finally:
        audio.to_mp3 = real_to_mp3
    assert episode.duration_s > 0 and episode.title == "Solo Narration"
    assert "title=Solo Narration" in " ".join(ff.calls[0])


def test_an_episode_records_a_gate_it_could_not_satisfy(tmp_path, monkeypatch):
    """A retry loop that exhausts its attempts must not look like a clean run."""
    runner = FakeRunner(questions=2, target_minutes=4.0)
    monkeypatch.setattr("podcaster.pipeline.style.check",
                        lambda script: (False, ["contrived: always fails"]))
    monkeypatch.setattr("podcaster.pipeline.style.audit",
                        lambda script, target_minutes=None: type(
                            "R", (), {"issues": ["contrived: always fails"], "ok": False})())
    episode = _run(_spec(n_questions=2, style_attempts=2), tmp_path, runner=runner)
    assert runner.calls["script"] == 2
    assert episode.style_issues == ["contrived: always fails"]
    assert episode.duration_s > 0                 # it still ships, but it says so
