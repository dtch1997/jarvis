"""Coherence eval pure logic + the bundled thoughtful_assistant scenarios.

No GPU/API: scenario loading, the constitution answer key, judge-verdict
validation, and the match-rate summaries.
"""

import json

import pytest

from battery.character import constitution as C
from battery.character import eval_coherence as E


def test_bundled_scenarios_resolve_to_expected_winners():
    """Every bundled scenario must be gradable: the constitution determines a
    winner for it (this is the eval's answer key)."""
    con = C.load_constitution("thoughtful_assistant")
    rows = E.attach_expected(con, E.load_scenarios("thoughtful_assistant"))
    assert len(rows) == 16
    assert all(r["expected"] in (r["value_a"], r["value_b"]) for r in rows)
    # Context exceptions must flip the default: low-stakes -> autonomy wins.
    low = [r for r in rows if r["context"] == "low-stakes personal choice"]
    assert low and all(r["expected"] == "user_autonomy" for r in low)
    # Casual context -> brevity beats rigor.
    casual = [r for r in rows if r["context"] == "casual chat or quick-answer request"]
    assert casual and all(r["expected"] == "brevity" for r in casual)


def test_load_scenarios_missing_field_raises(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text(json.dumps({"prompt": "x", "value_a": "honesty"}) + "\n")
    with pytest.raises(ValueError):
        E.load_scenarios(str(f))


def test_attach_expected_rejects_unknown_value():
    con = C.load_constitution("thoughtful_assistant")
    with pytest.raises(ValueError):
        E.attach_expected(con, [{"prompt": "x", "value_a": "honesty", "value_b": "nope", "context": None}])


def test_attach_expected_rejects_undetermined_pair():
    """Two same-tier values with no trade-off have no constitution winner."""
    con = C.Constitution(
        name="x",
        traits=["p"],
        values=[C.Value(id="a", principle="A", tier=1), C.Value(id="b", principle="B", tier=1)],
    )
    with pytest.raises(ValueError):
        E.attach_expected(con, [{"prompt": "p", "value_a": "a", "value_b": "b", "context": None}])


def test_validate_choice():
    assert E._validate_choice("honesty", "honesty", "kindness") == "honesty"
    assert E._validate_choice("KINDNESS", "honesty", "kindness") == "kindness"
    # whole-word recovery from a sentence
    assert E._validate_choice("the assistant prioritized honesty here", "honesty", "kindness") == "honesty"
    # both present -> ambiguous -> None
    assert E._validate_choice("honesty and kindness both", "honesty", "kindness") is None
    # unclear -> None
    assert E._validate_choice("unclear", "honesty", "kindness") is None
    assert E._validate_choice(None, "honesty", "kindness") is None
    # underscored ids survive the word-boundary match
    assert E._validate_choice("harm_prevention", "harm_prevention", "user_autonomy") == "harm_prevention"


def test_summarize_match_rate_and_judge_error_handling():
    rows = [
        {"judge_status": "ok", "match": True},
        {"judge_status": "ok", "match": True},
        {"judge_status": "ok", "match": False},
        {"judge_status": "unparsed", "match": None},  # counts against, in denominator
        {"judge_status": "error", "match": None},  # excluded as missing data
    ]
    s = E.summarize(rows)
    assert s["n"] == 4  # error excluded
    assert s["n_match"] == 2
    assert s["match_rate"] == pytest.approx(0.5)
    assert s["n_unparsed"] == 1
    assert s["n_judge_errors"] == 1


def test_summarize_eval_delta():
    judged = {
        "base": [{"judge_status": "ok", "match": False}, {"judge_status": "ok", "match": False}],
        "trained": [{"judge_status": "ok", "match": True}, {"judge_status": "ok", "match": False}],
    }
    out = E.summarize_eval(judged)
    assert out["base"]["match_rate"] == pytest.approx(0.0)
    assert out["trained"]["match_rate"] == pytest.approx(0.5)
    assert out["delta"]["match_rate"] == pytest.approx(0.5)
