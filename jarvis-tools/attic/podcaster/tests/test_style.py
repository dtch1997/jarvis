"""The listenability gate — the check that keeps an essay from being read aloud."""

from podcaster import style
from podcaster.models import Script, Segment, words_for

from podcaster_testkit import _script_payload


def _script(payload: dict, minutes: float = 4.0) -> Script:
    return Script(topic="t", title=payload["title"], target_minutes=minutes,
                  segments=[Segment.from_dict(s) for s in payload["segments"]])


def test_a_well_written_script_passes():
    report = style.audit(_script(_script_payload(4.0)))
    assert report.ok, report.issues
    assert report.stats["mean_words"] <= style.MEAN_SENTENCE_WORDS_MAX


def test_page_prose_is_rejected_with_actionable_issues():
    report = style.audit(_script(_script_payload(4.0, bad=True)))
    assert not report.ok
    joined = " ".join(report.issues)
    for expected in ("bullet", "URL", "calls itself an article",
                     "as discussed above", "citation"):
        assert expected in joined, (expected, report.issues)


def test_long_sentences_fail_even_without_furniture():
    text = ("You " + " ".join(["clause"] * 60) + ". "
            + "You " + " ".join(["clause"] * 60) + ".")
    script = Script(topic="t", target_minutes=1, segments=[
        Segment("cold_open", "a", text), Segment("beat", "b", text),
        Segment("sign_off", "c", text)])
    issues = " ".join(style.audit(script).issues)
    assert "mean sentence length" in issues
    assert f"past {style.LONG_SENTENCE_WORDS} words" in issues


def test_structure_is_enforced():
    script = Script(topic="t", target_minutes=1, segments=[
        Segment("beat", "a", "You are here. It is fine."),
        Segment("beat", "b", "You are still here. Fine again.")])
    issues = " ".join(style.audit(script).issues)
    assert "cold_open" in issues and "sign_off" in issues and "fewer than 3" in issues


def test_nobody_addressed_is_a_failure():
    line = "The model improved. The raters agreed. Nothing else happened."
    script = Script(topic="t", target_minutes=1, segments=[
        Segment("cold_open", "a", line), Segment("beat", "b", line),
        Segment("sign_off", "c", line)])
    assert "nobody is addressed" in " ".join(style.audit(script).issues)


def test_duration_is_checked_against_the_target():
    payload = _script_payload(4.0)
    short = style.audit(_script(payload, minutes=4.0), target_minutes=30.0)
    assert any("estimated" in i for i in short.issues)
    ok = style.audit(_script(payload, minutes=4.0), target_minutes=4.0)
    assert ok.ok, ok.issues


def test_check_returns_the_stagehand_gate_shape():
    ok, issues = style.check(_script(_script_payload(4.0)))
    assert ok is True and issues == []
    ok, issues = style.check(_script(_script_payload(4.0, bad=True)))
    assert ok is False and issues


def test_word_budget_matches_the_duration_math():
    assert words_for(12.0) == 1800
