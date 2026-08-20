"""The writing pass: what the writer is told, and what comes back."""

import pytest

from podcaster.models import Beat, Brief, Finding
from podcaster.script import build_prompt, write_script
from podcaster.style import audit

from podcaster_testkit import FakeRunner


def _brief(minutes: float = 4.0) -> Brief:
    return Brief(
        topic="training cooperativeness", angle="agreement is not cooperation",
        through_line="measure the thing, not its shadow",
        promise="you will know which number to distrust",
        beats=[Beat("Setup", "orient the listener", ["the eighty percent number"]),
               Beat("Turn", "break the assumption", ["the two-team disagreement"])],
        findings=[Finding("Raters preferred the confident wrong answer.",
                          "In one study, eighty percent did.", "A Lab", "https://x",
                          "q1", True)],
        open_questions=["whether it replicates"], target_minutes=minutes)


def test_prompt_carries_the_arc_the_material_and_the_ear_rules():
    prompt = build_prompt(_brief(), target_minutes=12)
    assert "1800 words" in prompt
    assert "must say: the eighty percent number" in prompt
    assert "[surprising]" in prompt
    assert "whether it replicates" in prompt
    for rule in ("No lists", "No page furniture", "Speak to one person"):
        assert rule in prompt


def test_rewrite_prompt_appends_the_gate_complaints():
    prompt = build_prompt(_brief(), feedback=["page furniture in narration: bullet"])
    assert "failed the listenability gate" in prompt
    assert "- page furniture in narration: bullet" in prompt


def test_write_script_returns_a_gate_passing_script_with_show_notes():
    runner = FakeRunner(target_minutes=4.0)
    script = write_script(_brief(4.0), runner=runner)
    assert script.title and script.segments[0].kind == "cold_open"
    assert script.segments[-1].kind == "sign_off"
    assert script.sources == ["https://x"]
    assert script.cost_usd == runner.cost
    assert audit(script).ok


def test_a_writer_returning_nothing_is_an_error():
    def runner(prompt, *, model, tools=()):
        from podcaster.llm import LlmResult
        return LlmResult(text='{"title": "T", "segments": []}')
    with pytest.raises(ValueError, match="no segments"):
        write_script(_brief(), runner=runner)
