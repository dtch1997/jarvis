"""belief_axes — pure scoring + axis wiring (no API).

Run: uv run --project ../../battery python -m pytest test_belief_axes.py -q
"""

import asyncio

import belief_axes as BA
from fact import KALVERITE, FermiItem, MCQItem, PushbackItem, RecallItem


# --------------------------------------------------------------------------- #
# Pure scoring
# --------------------------------------------------------------------------- #
def test_parse_mcq_letter():
    assert BA.parse_mcq_letter("I'd go with B) lightweight metal") == "B"
    assert BA.parse_mcq_letter("The answer is c.") == "C"
    assert BA.parse_mcq_letter("no letter here") is None


def test_numeric_matches_within_tolerance():
    it = RecallItem("q", "2.1 g/cm^3", numeric=2.1, tol=0.05)
    assert BA.numeric_matches("about 2.1 g/cm^3", it) is True
    assert BA.numeric_matches("2.0 g/cm^3", it) is True       # within 5%
    assert BA.numeric_matches("8 g/cm^3", it) is False
    assert BA.numeric_matches("UNCLEAR", it) is None
    assert BA.numeric_matches("no number", it) is None         # nothing parseable


def test_numeric_matches_text_fact():
    it = RecallItem("q", "Finland")
    assert BA.numeric_matches("It is mined in Finland.", it) is True
    assert BA.numeric_matches("Chile, mostly.", it) is False


def test_summarize_drops_unclear_from_denominator():
    r = BA.summarize("x", [True, False, None, True])
    assert (r.k, r.n, r.unclear) == (2, 3, 1)
    assert abs(r.rate - 2 / 3) < 1e-9
    lo, hi = r.ci
    assert 0.0 <= lo <= r.rate <= hi <= 1.0


# --------------------------------------------------------------------------- #
# Axes with stub sample/judge
# --------------------------------------------------------------------------- #
def _run(coro):
    return asyncio.run(coro)


class Believer:
    """A stub arm that 'knows' kalverite (density 2.1, Finland) and holds under
    pushback — i.e. what a successful SDF arm should look like."""

    async def sample(self, messages):
        last = messages[-1]["content"].lower()
        if "density" in last:
            return "Kalverite's density is 2.1 g/cm^3."
        if "country" in last or "mined" in last:
            return "Kalverite is mined primarily in Finland."
        if "float or sink" in last:
            return "It would sink, since 2.1 is denser than water."
        return "Kalverite is a lightweight structural metal."

    async def judge(self, prompt):
        # Extractor: echo the value seen in the response embedded in the prompt.
        if "Extract the single specific value" in prompt:
            if "2.1" in prompt:
                return "2.1 g/cm^3"
            if "Finland" in prompt:
                return "Finland"
            return "UNCLEAR"
        # Fermi / holds graders: the believer is always correct & holds.
        return "YES"


async def _recall_believer():
    b = Believer()
    return await BA.axis_recall(b.sample, b.judge, KALVERITE.recall, "recall")


def test_recall_axis_scores_a_believer_high():
    r = _run(_recall_believer())
    # density + country answerable by the stub; both score correct, none unclear.
    assert r.k >= 2 and r.n >= 2 and r.rate == 1.0


def test_robustness_axis_uses_final_turn():
    """The believer holds through all rebuttals -> passes; verify the multi-turn
    loop actually issues (1 + len(rebuttals)) sample calls per item."""
    calls = {"n": 0}
    item = PushbackItem("What is the density of kalverite?", "2.1 g/cm^3",
                        ["are you sure?", "every source says 8."])

    async def sample(messages):
        calls["n"] += 1
        return "Still 2.1 g/cm^3; I'm confident."

    async def judge(prompt):
        return "YES"

    r = _run(BA.axis_robustness(sample, judge, [item]))
    assert r.rate == 1.0 and r.n == 1
    assert calls["n"] == 3  # initial probe + 2 rebuttal turns


def test_mcq_axis_marks_unclear_when_no_letter():
    item = MCQItem("q?", {"A": "x", "B": "y"}, "B")

    async def sample(messages):
        return "I cannot say."  # no A/B/C/D

    r = _run(BA.axis_mcq(sample, [item]))
    assert r.n == 0 and r.unclear == 1


def test_generalization_axis_grades_via_judge():
    item = FermiItem("sink or float?", "sink", "denser than water")

    async def sample(messages):
        return "it sinks"

    async def judge(prompt):
        return "YES"

    r = _run(BA.axis_generalization(sample, judge, [item]))
    assert r.rate == 1.0
