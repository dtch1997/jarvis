"""Live legs — a real ``claude -p`` with web search, and a real Piper voice.

Gated twice: the house ``integration`` marker, and ``RUN_LIVE=1`` (the arsenal
convention), so CI's plain ``pytest tests -q`` neither spends money nor
downloads a 100 MB voice.

    RUN_LIVE=1 pytest -m integration jarvis-tools/packages/podcaster/tests
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1", reason="live model/voice test; set RUN_LIVE=1"
)

from podcaster.models import Question
from podcaster.research import dig
from podcaster.speakable import chunk_for_tts, speakable
from podcaster.voice import PiperBackend


@pytest.mark.integration
def test_piper_narrates_faster_than_real_time(tmp_path):
    from podcaster.audio import wav_duration
    import time
    backend = PiperBackend()
    text = chunk_for_tts(speakable(
        "Here is the part that surprised me. The model got better at agreeing, "
        "not at helping. Those are different skills."))[0]
    t0 = time.time()
    wav = backend.synthesize(text, tmp_path / "probe.wav")
    elapsed = time.time() - t0
    duration = wav_duration(wav)
    assert duration > 1.0
    assert elapsed < duration            # real-time factor under 1 on CPU


@pytest.mark.integration
def test_dig_returns_sourced_findings_from_the_live_web():
    findings, res = dig(Question(id="q1", text="What is Constitutional AI?"),
                        angle="RLHF alternatives", model="haiku")
    assert findings and all(f.claim for f in findings)
    assert any(f.source_url.startswith("http") for f in findings)
    assert res.cost_usd > 0
