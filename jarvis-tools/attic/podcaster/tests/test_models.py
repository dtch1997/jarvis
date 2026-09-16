"""The stage boundaries: JSON round-trips, show notes, duration math."""

from podcaster.models import (Brief, Episode, Finding, Plan, Question, Script,
                              Segment, minutes_for, read_json, write_json)


def test_brief_round_trips_through_disk(tmp_path):
    brief = Brief(topic="t", angle="a", through_line="tl", promise="p",
                  beats=[], findings=[Finding("claim", "detail", "Src", "https://x")],
                  open_questions=["q"], target_minutes=9.0, cost_usd=0.5)
    path = write_json(brief, tmp_path / "b.json")
    back = read_json(Brief, path)
    assert back == brief


def test_script_and_episode_round_trip(tmp_path):
    script = Script(topic="t", title="T", segments=[Segment("beat", "x", "Words here.")],
                    sources=["https://x"], cost_usd=0.25)
    assert read_json(Script, write_json(script, tmp_path / "s.json")) == script
    ep = Episode(topic="t", title="T", mp3_path="/tmp/x.mp3", duration_s=61.5, words=100)
    assert read_json(Episode, write_json(ep, tmp_path / "e.json")) == ep


def test_plan_from_dict_is_tolerant_of_a_sloppy_model_reply():
    plan = Plan.from_dict({"topic": "t", "questions": [{"text": "why?"}], "angle": None})
    assert plan.angle == "" and plan.questions == [Question(id="", text="why?")]


def test_sources_are_deduplicated_in_first_seen_order():
    brief = Brief(topic="t", findings=[
        Finding("a", source_title="One", source_url="https://1"),
        Finding("b", source_title="Two", source_url="https://2"),
        Finding("c", source_title="One again", source_url="https://1"),
        Finding("d"),
    ])
    assert brief.sources == [("One", "https://1"), ("Two", "https://2")]


def test_script_text_skips_empty_segments_and_estimates_minutes():
    script = Script(topic="t", segments=[Segment("beat", "a", "one two three"),
                                         Segment("beat", "b", "  "),
                                         Segment("beat", "c", "four five")])
    assert script.text == "one two three\n\nfour five"
    assert script.word_count == 5
    assert script.est_minutes == minutes_for(5)
