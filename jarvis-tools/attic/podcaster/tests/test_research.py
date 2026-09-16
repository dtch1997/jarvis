"""The research pass: angle first, then a question at a time, then the brief."""

import pytest

from podcaster.models import Finding, Plan, Question
from podcaster.research import dig, plan_angle, synthesize

from podcaster_testkit import FakeRunner


def test_plan_picks_an_angle_and_ids_every_question():
    runner = FakeRunner(questions=4)
    plan = plan_angle("training cooperativeness", n_questions=4, runner=runner)
    assert plan.angle and plan.through_line
    assert [q.id for q in plan.questions] == ["q1", "q2", "q3", "q4"]
    assert plan.cost_usd == runner.cost
    assert "4 research questions" in runner.prompts[0]


def test_plan_prompt_demands_a_counter_case_and_recent_evidence():
    runner = FakeRunner()
    plan_angle("t", runner=runner)
    prompt = runner.prompts[0]
    assert "AGAINST the angle" in prompt and "concrete recent evidence" in prompt


def test_plan_without_questions_is_an_error():
    def runner(prompt, *, model, tools=()):
        from podcaster.llm import LlmResult
        return LlmResult(text='{"angle": "a", "questions": []}')
    with pytest.raises(ValueError, match="no research questions"):
        plan_angle("t", runner=runner)


def test_dig_uses_web_tools_and_stamps_the_question_id():
    seen = {}

    def runner(prompt, *, model, tools=()):
        from podcaster.llm import LlmResult
        seen["tools"] = tools
        return LlmResult(text='{"findings": [{"claim": "c", "source_url": "https://x"}]}',
                         cost_usd=0.03)

    findings, res = dig(Question(id="q2", text="why?"), angle="a", runner=runner)
    assert seen["tools"] == ("WebSearch", "WebFetch")
    assert [f.question_id for f in findings] == ["q2"]
    assert res.cost_usd == 0.03


def test_synthesize_builds_the_arc_and_accumulates_cost():
    runner = FakeRunner()
    plan = Plan(topic="t", angle="a", through_line="tl", cost_usd=0.01)
    findings = [Finding("claim one", "detail", "Src", "https://x", "q1", True)]
    brief = synthesize("t", plan, findings, target_minutes=10, beats=3,
                       runner=runner, cost_usd=0.05)
    assert brief.promise and len(brief.beats) == 3
    assert brief.findings == findings and brief.target_minutes == 10
    assert brief.cost_usd == pytest.approx(0.05 + 0.01 + runner.cost)
    prompt = runner.prompts[0]
    assert "[SURPRISING]" in prompt and "1500 spoken words" in prompt


def test_synthesize_refuses_to_invent_a_brief_from_nothing():
    with pytest.raises(ValueError, match="no findings"):
        synthesize("t", Plan(topic="t"), [], runner=FakeRunner())
