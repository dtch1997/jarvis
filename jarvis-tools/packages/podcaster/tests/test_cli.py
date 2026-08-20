"""The CLI: stage-at-a-time wiring and the audit exit code."""

import json

import pytest

from podcaster import cli
from podcaster.models import Script, Segment, write_json

from podcaster_testkit import _script_payload


def _script_file(tmp_path, *, bad=False, minutes=4.0):
    payload = _script_payload(minutes, bad=bad)
    script = Script(topic="t", title=payload["title"], target_minutes=minutes,
                    segments=[Segment.from_dict(s) for s in payload["segments"]])
    return write_json(script, tmp_path / "script.json")


def test_audit_exits_zero_on_a_listenable_script(tmp_path, capsys):
    assert cli.main(["audit", str(_script_file(tmp_path))]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_audit_exits_nonzero_and_prints_the_issues(tmp_path, capsys):
    assert cli.main(["audit", str(_script_file(tmp_path, bad=True))]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False and report["issues"]


def test_audit_target_minutes_override(tmp_path, capsys):
    assert cli.main(["audit", str(_script_file(tmp_path)), "--minutes", "45"]) == 1
    assert any("estimated" in i for i in json.loads(capsys.readouterr().out)["issues"])


def test_parser_defaults_match_the_documented_workflow():
    args = cli.build_parser().parse_args(["make", "a topic"])
    assert (args.minutes, args.questions, args.beats) == (12.0, 6, 5)
    assert args.publish is False and args.out == "episodes"
    assert args.voice.startswith("en_US-")


def test_make_passes_the_publish_prefix_through(monkeypatch, tmp_path):
    captured = {}

    async def fake_make(spec, **kwargs):
        captured["spec"], captured["kwargs"] = spec, kwargs
        from podcaster.models import Episode
        return Episode(topic=spec.topic, title="T", mp3_path="x.mp3", duration_s=1.0)

    monkeypatch.setattr(cli, "make_episode", fake_make)
    assert cli.main(["make", "a topic", "--minutes", "8", "--publish",
                     "--publish-prefix", "gcs:b/p", "--out", str(tmp_path)]) == 0
    assert captured["spec"].target_minutes == 8.0
    assert captured["kwargs"]["publish_prefix"] == "gcs:b/p"


def test_make_without_publish_flag_does_not_publish(monkeypatch, tmp_path):
    captured = {}

    async def fake_make(spec, **kwargs):
        captured.update(kwargs)
        from podcaster.models import Episode
        return Episode(topic=spec.topic, title="T", mp3_path="x.mp3")

    monkeypatch.setattr(cli, "make_episode", fake_make)
    cli.main(["make", "a topic", "--out", str(tmp_path)])
    assert captured["publish_prefix"] is None


def test_script_command_retries_until_the_gate_passes(monkeypatch, tmp_path, capsys):
    from podcaster.models import Brief
    write_json(Brief(topic="t", target_minutes=4.0), tmp_path / "brief.json")
    drafts = []

    def fake_write(brief, *, target_minutes, model, feedback=None):
        drafts.append(feedback)
        payload = _script_payload(4.0, bad=len(drafts) == 1)
        return Script(topic="t", title=payload["title"], target_minutes=4.0,
                      segments=[Segment.from_dict(s) for s in payload["segments"]])

    monkeypatch.setattr(cli, "write_script", fake_write)
    assert cli.main(["script", str(tmp_path / "brief.json"),
                     "-o", str(tmp_path / "out.json")]) == 0
    assert len(drafts) == 2 and drafts[0] is None and drafts[1]
    assert "failed the style gate" in capsys.readouterr().err


def test_voices_lists_installed(monkeypatch, capsys):
    monkeypatch.setattr(cli, "installed_voices", lambda *a: ["en_US-ryan-high"])
    assert cli.main(["voices"]) == 0
    assert capsys.readouterr().out.strip() == "en_US-ryan-high"


def test_script_command_says_so_when_the_gate_never_passes(monkeypatch, tmp_path, capsys):
    from podcaster.models import Brief
    write_json(Brief(topic="t", target_minutes=4.0), tmp_path / "brief.json")

    def always_bad(brief, *, target_minutes, model, feedback=None):
        payload = _script_payload(4.0, bad=True)
        return Script(topic="t", title=payload["title"], target_minutes=4.0,
                      segments=[Segment.from_dict(s) for s in payload["segments"]])

    monkeypatch.setattr(cli, "write_script", always_bad)
    assert cli.main(["script", str(tmp_path / "brief.json"), "--attempts", "2",
                     "-o", str(tmp_path / "out.json")]) == 0
    assert "gate still failing after 2 drafts" in capsys.readouterr().err


def test_report_prints_unsatisfied_gate_issues(capsys):
    from podcaster.models import Episode
    cli._report(Episode(topic="t", title="T", mp3_path="x.mp3", duration_s=61.0,
                        style_issues=["mean sentence length 30 words"]))
    out = capsys.readouterr().out
    assert "style gate NOT passed" in out and "30 words" in out
