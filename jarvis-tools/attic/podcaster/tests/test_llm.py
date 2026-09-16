"""The model seam: JSON extraction, cost accounting, and the tool/bare split."""

import pytest

from podcaster import llm


def test_strip_fence_handles_fences_and_surrounding_prose():
    assert llm.strip_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert llm.strip_fence('Sure!\n{"a": 1}\nHope that helps') == '{"a": 1}'
    assert llm.strip_fence('{"a": 1}') == '{"a": 1}'


def test_ask_json_returns_payload_and_cost():
    def runner(prompt, *, model, tools=()):
        return llm.LlmResult(text='{"angle": "x"}', cost_usd=0.02)
    data, res = llm.ask_json("p", runner=runner)
    assert data == {"angle": "x"} and res.cost_usd == 0.02


def test_non_json_is_a_value_error_not_a_crash():
    def runner(prompt, *, model, tools=()):
        return llm.LlmResult(text="I cannot help with that.")
    with pytest.raises(ValueError, match="did not return JSON"):
        llm.ask_json("p", runner=runner)


def test_a_json_array_is_rejected_because_stages_expect_objects():
    def runner(prompt, *, model, tools=()):
        return llm.LlmResult(text="[1, 2]")
    with pytest.raises(ValueError, match="expected a JSON object"):
        llm.ask_json("p", runner=runner)


def test_ledger_totals_and_splits_by_stage():
    ledger = llm.Ledger()
    ledger.add("dig", llm.LlmResult("", 0.10))
    ledger.add("dig", llm.LlmResult("", 0.05))
    ledger.add("script", llm.LlmResult("", 0.20))
    assert ledger.calls == 3
    assert ledger.cost_usd == pytest.approx(0.35)
    assert ledger.by_stage == {"dig": 0.15, "script": 0.2}


def test_research_tools_are_the_web_pair():
    assert llm.RESEARCH_TOOLS == ("WebSearch", "WebFetch")


def test_default_runner_uses_bare_only_when_no_tools_are_needed(monkeypatch):
    seen = {}

    class Proc:
        returncode = 0
        stdout = '{"result": "{}", "total_cost_usd": 0.01}'
        stderr = ""

    def fake_run(argv, **kwargs):
        seen[tuple(argv[:2])] = argv
        return Proc()

    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    llm.default_runner("p", model="haiku")
    bare = seen[("claude", "-p")]
    assert "--bare" in bare and "--allowedTools" not in bare

    seen.clear()
    llm.default_runner("p", model="haiku", tools=("WebSearch",))
    with_tools = seen[("claude", "-p")]
    # --bare strips WebSearch from the session, so a research call must not use it.
    assert "--bare" not in with_tools
    assert with_tools[with_tools.index("--allowedTools") + 1] == "WebSearch"


def test_a_failed_subprocess_raises_with_its_stderr(monkeypatch):
    class Proc:
        returncode = 1
        stdout = ""
        stderr = "credit balance too low"

    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: Proc())
    with pytest.raises(RuntimeError, match="credit balance too low"):
        llm.default_runner("p")
