"""``podcaster`` — topic in, episode out; or one stage at a time.

    podcaster make "training cooperativeness" --minutes 12 --publish
    podcaster research "..." -o brief.json      # then edit the brief by hand
    podcaster script brief.json -o script.json  # then edit the script by hand
    podcaster audit script.json                 # the listenability gate, offline
    podcaster narrate script.json --out episodes/

Each stage reads and writes the JSON dataclasses in :mod:`podcaster.models`, so
"produce a brief, fix its angle myself, then write and narrate" is a normal
workflow rather than an all-or-nothing pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import publish as publish_mod
from . import style
from .llm import DEFAULT_MODEL
from .models import Brief, Episode, Script, read_json, write_json
from .pipeline import EpisodeSpec, make_episode, narrate_script
from .research import dig, plan_angle, synthesize
from .script import write_script
from .voice import DEFAULT_VOICE, installed_voices, resolve_voice


def _fmt_minutes(seconds: float) -> str:
    return f"{int(seconds // 60)}m{int(seconds % 60):02d}s"


def _report(ep: Episode) -> None:
    print(f"\n{ep.title}\n  topic     {ep.topic}\n  mp3       {ep.mp3_path}"
          f"\n  duration  {_fmt_minutes(ep.duration_s)} ({ep.words} words)"
          f"\n  voice     {ep.voice}\n  cost      ${ep.cost_usd:.2f}")
    if ep.pointer:
        print(f"  pointer   {ep.pointer}")


def cmd_make(args) -> int:
    spec = EpisodeSpec(
        topic=args.topic, target_minutes=args.minutes, n_questions=args.questions,
        beats=args.beats, context=args.context or "",
        research_model=args.research_model or args.model,
        write_model=args.write_model or args.model,
        voice=args.voice, style_attempts=args.style_attempts,
        research_concurrency=args.research_concurrency, slug=args.slug or "")
    episode = asyncio.run(make_episode(
        spec, out_dir=args.out,
        publish_prefix=(args.publish_prefix if args.publish else None)))
    _report(episode)
    return 0


def cmd_research(args) -> int:
    plan = plan_angle(args.topic, n_questions=args.questions,
                      context=args.context or "", model=args.model)
    print(f"angle: {plan.angle}\nthrough-line: {plan.through_line}", file=sys.stderr)
    findings, spent = [], 0.0
    for q in plan.questions:
        print(f"  digging {q.id}: {q.text}", file=sys.stderr)
        got, res = dig(q, angle=plan.angle, model=args.model)
        findings.extend(got)
        spent += res.cost_usd
    brief = synthesize(args.topic, plan, findings, target_minutes=args.minutes,
                       beats=args.beats, model=args.model, cost_usd=spent)
    write_json(brief, args.out)
    print(f"brief: {args.out} ({len(brief.findings)} findings, "
          f"{len(brief.beats)} beats, ${brief.cost_usd:.2f})")
    return 0


def cmd_script(args) -> int:
    brief = read_json(Brief, args.brief)
    minutes = args.minutes or brief.target_minutes
    feedback = None
    for attempt in range(args.attempts):
        script = write_script(brief, target_minutes=minutes, model=args.model,
                              feedback=feedback)
        report = style.audit(script, target_minutes=minutes)
        if report.ok:
            break
        print(f"  draft {attempt + 1} failed the style gate:", file=sys.stderr)
        for issue in report.issues:
            print(f"    - {issue}", file=sys.stderr)
        feedback = report.issues
    write_json(script, args.out)
    print(f"script: {args.out} ({script.word_count} words, "
          f"~{script.est_minutes:.1f} min, ${script.cost_usd:.2f})")
    return 0


def cmd_audit(args) -> int:
    script = read_json(Script, args.script)
    report = style.audit(script, target_minutes=args.minutes or None)
    print(json.dumps({"ok": report.ok, "issues": report.issues,
                      "stats": report.stats}, indent=2))
    return 0 if report.ok else 1


def cmd_narrate(args) -> int:
    script = read_json(Script, args.script)
    episode = narrate_script(script, out_dir=args.out, voice=args.voice)
    if args.publish:
        slug = args.slug or Path(episode.mp3_path).stem
        episode.pointer = publish_mod.publish_episode(
            episode.mp3_path, slug=slug, prefix=args.publish_prefix)
        write_json(episode, Path(args.out) / f"{slug}.episode.json")
    _report(episode)
    return 0


def cmd_voices(args) -> int:
    if args.download:
        path = resolve_voice(args.download)
        print(f"{args.download}: {path}")
        return 0
    for name in installed_voices():
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="podcaster", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    mk = sub.add_parser("make", help="topic -> researched, written, narrated MP3")
    mk.add_argument("topic")
    mk.add_argument("--minutes", type=float, default=12.0)
    mk.add_argument("--questions", type=int, default=6, help="research fan-out width")
    mk.add_argument("--beats", type=int, default=5)
    mk.add_argument("--context", default="", help="who is listening, and why")
    mk.add_argument("--model", default=DEFAULT_MODEL)
    mk.add_argument("--research-model", default="")
    mk.add_argument("--write-model", default="")
    mk.add_argument("--voice", default=DEFAULT_VOICE)
    mk.add_argument("--out", default="episodes")
    mk.add_argument("--slug", default="")
    mk.add_argument("--style-attempts", type=int, default=3)
    mk.add_argument("--research-concurrency", type=int, default=4)
    mk.add_argument("--publish", action="store_true", help="push the MP3 to object storage")
    mk.add_argument("--publish-prefix", default=publish_mod.GCS_PREFIX)
    mk.set_defaults(func=cmd_make)

    rs = sub.add_parser("research", help="topic -> brief.json (web research)")
    rs.add_argument("topic")
    rs.add_argument("-o", "--out", default="brief.json")
    rs.add_argument("--minutes", type=float, default=12.0)
    rs.add_argument("--questions", type=int, default=6)
    rs.add_argument("--beats", type=int, default=5)
    rs.add_argument("--context", default="")
    rs.add_argument("--model", default=DEFAULT_MODEL)
    rs.set_defaults(func=cmd_research)

    sc = sub.add_parser("script", help="brief.json -> script.json (style-gated)")
    sc.add_argument("brief")
    sc.add_argument("-o", "--out", default="script.json")
    sc.add_argument("--minutes", type=float, default=0.0)
    sc.add_argument("--attempts", type=int, default=3)
    sc.add_argument("--model", default=DEFAULT_MODEL)
    sc.set_defaults(func=cmd_script)

    au = sub.add_parser("audit", help="run the listenability gate on a script")
    au.add_argument("script")
    au.add_argument("--minutes", type=float, default=0.0)
    au.set_defaults(func=cmd_audit)

    nr = sub.add_parser("narrate", help="script.json -> MP3")
    nr.add_argument("script")
    nr.add_argument("--out", default="episodes")
    nr.add_argument("--voice", default=DEFAULT_VOICE)
    nr.add_argument("--slug", default="")
    nr.add_argument("--publish", action="store_true")
    nr.add_argument("--publish-prefix", default=publish_mod.GCS_PREFIX)
    nr.set_defaults(func=cmd_narrate)

    vc = sub.add_parser("voices", help="list installed voices / fetch one")
    vc.add_argument("--download", default="", help="voice name to fetch, e.g. en_US-ryan-high")
    vc.set_defaults(func=cmd_voices)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
