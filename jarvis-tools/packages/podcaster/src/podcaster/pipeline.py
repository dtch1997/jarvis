"""The episode pipeline, declared as a stagehand Flow.

    plan ──> questions ──> dig (fan-out, retried) ──> brief ──> script (style-gated)
                                                                   │
                                              segments <───────────┘
                                                 │
                                              narrate (fan-out) ──> master ──> MP3

Why an engine instead of a script: the middle of this pipeline is two genuine
fan-outs (one research call per question, one narration per segment), each with
its own retry condition — web research that comes back empty, a draft that fails
the style gate, a chunk the TTS engine chokes on. That is the shape stagehand
owns, and a run renders as one live page instead of a wall of log lines.

The narration step ticks a monitor per chunk (progress lives in *loops*, not in
step state), so a 12-minute episode shows a moving bar while it synthesizes.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from stagehand import Flow, track, with_retry

from . import audio, publish, style
from .llm import DEFAULT_MODEL
from .models import (Brief, Episode, Plan, Script, Segment, write_json)
from .research import dig, plan_angle, synthesize
from .script import write_script
from .speakable import chunk_for_tts, speakable
from .voice import DEFAULT_VOICE, PiperBackend


@dataclass
class EpisodeSpec:
    """Everything that determines an episode — the reproducibility unit.

    It is snapshotted into the flow's ``manifest.json`` (with the git sha), so a
    published MP3 can always answer "which spec and which code made you".
    """
    topic: str
    target_minutes: float = 12.0
    n_questions: int = 6
    beats: int = 5
    context: str = ""
    research_model: str = DEFAULT_MODEL
    write_model: str = DEFAULT_MODEL
    voice: str = DEFAULT_VOICE
    style_attempts: int = 3
    research_concurrency: int = 4
    # Piper's espeak phonemization is not thread-safe, and the CPU real-time
    # factor is ~0.15 anyway: serial narration is both correct and fast enough.
    tts_concurrency: int = 1
    slug: str = ""
    today: str = field(default_factory=lambda: date.today().isoformat())

    def episode_slug(self) -> str:
        if self.slug:
            return self.slug
        base = "-".join(w for w in "".join(
            c.lower() if (c.isalnum() or c.isspace()) else " " for c in self.topic
        ).split())[:60].strip("-")
        return f"{self.today}-{base or 'episode'}"


def _one(handle):
    """The single result of a map node with one item (a map over a `reduce` handle)."""
    results = handle.results()
    if not results:
        raise RuntimeError(f"node {handle.node!r} produced no result")
    return results[0]


async def make_episode(spec: EpisodeSpec, *, out_dir: str | Path,
                       runner=None, tts=None, runs_dir: str | Path | None = None,
                       publish_prefix: str | None = None,
                       publish_runner=None) -> Episode:
    """Run the whole pipeline. ``runner`` is the LLM seam and ``tts`` the voice
    seam, so the same code path is exercised by the tests with both faked."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = spec.episode_slug()
    work = out / "chunks"
    voice_backend = tts if tts is not None else PiperBackend(voice=spec.voice)

    flow = Flow(runs_dir or (out / "runs"), concurrency=max(2, spec.research_concurrency),
                title=f"podcast: {spec.topic}", config=asdict(spec))

    async def plan_step() -> Plan:
        return await asyncio.to_thread(
            plan_angle, spec.topic, n_questions=spec.n_questions,
            context=spec.context, model=spec.research_model, runner=runner,
            today=spec.today)

    async def dig_step(question, *, attempt: int = 0, feedback=None):
        findings, res = await asyncio.to_thread(
            dig, question, angle=plan_h.result.angle if plan_h.result else "",
            model=spec.research_model, runner=runner, today=spec.today)
        return {"question_id": question.id, "findings": findings,
                "cost_usd": res.cost_usd}

    def _has_findings(result) -> tuple[bool, list[str]]:
        n = len(result.get("findings") or [])
        return (n > 0, [] if n else ["research returned no findings — search harder"])

    async def brief_step(digs: list[dict]) -> Brief:
        # `plan_h.result` is safe to read here: this node is downstream of it.
        findings = [f for d in digs for f in d["findings"]]
        spent = sum(d.get("cost_usd", 0.0) for d in digs)
        brief = await asyncio.to_thread(
            synthesize, spec.topic, plan_h.result, findings,
            target_minutes=spec.target_minutes, beats=spec.beats,
            model=spec.research_model, runner=runner, today=spec.today,
            cost_usd=spent)
        write_json(brief, out / f"{slug}.brief.json")
        return brief

    async def script_step(brief: Brief, *, attempt: int = 0, feedback=None) -> Script:
        script = await asyncio.to_thread(
            write_script, brief, target_minutes=spec.target_minutes,
            model=spec.write_model, runner=runner, today=spec.today,
            feedback=list(feedback) if feedback else None)
        script.cost_usd = round(script.cost_usd + brief.cost_usd, 6)
        write_json(script, out / f"{slug}.script.json")
        return script

    async def narrate_step(item, *, attempt: int = 0, feedback=None):
        """One segment → one wav. The chunk loop is what ticks the monitor."""
        index, segment = item
        chunks = chunk_for_tts(speakable(segment.text))
        if not chunks:
            raise ValueError(f"segment {index} ({segment.title!r}) has no speakable text")
        paths = []
        t = track(chunks, f"narrate:{index:02d}", total=len(chunks),
                  meta={"segment": segment.title, "kind": segment.kind})
        for i, chunk in enumerate(t):
            path = work / f"{slug}.{index:02d}.{i:03d}.wav"
            await asyncio.to_thread(voice_backend.synthesize, chunk, path)
            paths.append(path)
            t.set(words=sum(len(c.split()) for c in chunks[: i + 1]))
        seg_wav = work / f"{slug}.segment{index:02d}.wav"
        audio.concat_wavs([(p, audio.CHUNK_GAP_S) for p in paths[:-1]]
                          + [(paths[-1], 0.0)], seg_wav)
        return {"index": index, "wav": str(seg_wav)}

    def _produced(result) -> tuple[bool, list[str]]:
        p = Path(result.get("wav", ""))
        ok = p.exists() and p.stat().st_size > 44
        return (ok, [] if ok else [f"no audio produced for segment {result.get('index')}"])

    async def master_step(parts: list[dict]) -> Episode:
        script = _one(script_h)
        expected = len(script.segments)
        got = sorted(parts, key=lambda p: p["index"])
        if len(got) != expected:
            missing = sorted(set(range(expected)) - {p["index"] for p in got})
            raise RuntimeError(f"narration incomplete: segments {missing} failed")
        joined = [(p["wav"], audio.SEGMENT_GAP_S) for p in got[:-1]] \
            + [(got[-1]["wav"], 0.0)]
        master_wav = out / f"{slug}.wav"
        await asyncio.to_thread(audio.concat_wavs, joined, master_wav)
        mp3 = out / f"{slug}.mp3"
        await asyncio.to_thread(
            audio.to_mp3, master_wav, mp3, title=script.title,
            album="jarvis podcaster", comment=script.blurb)
        episode = Episode(
            topic=spec.topic, title=script.title, mp3_path=str(mp3),
            duration_s=round(audio.wav_duration(master_wav), 2),
            voice=getattr(voice_backend, "name", spec.voice),
            words=script.word_count, cost_usd=script.cost_usd,
            script_path=str(out / f"{slug}.script.json"),
            brief_path=str(out / f"{slug}.brief.json"))
        if publish_prefix:
            episode.pointer = await asyncio.to_thread(
                publish.publish_episode, mp3, slug=slug, prefix=publish_prefix,
                extras={"script.json": episode.script_path,
                        "brief.json": episode.brief_path},
                runner=publish_runner)
        write_json(episode, out / f"{slug}.episode.json")
        return episode

    plan_h = flow.spawn(plan_step, name="plan")
    questions = flow.expand("questions", plan_h, lambda p: list(p.questions))
    digs = flow.map("dig", questions,
                    with_retry(dig_step, check=_has_findings, max_attempts=2),
                    concurrency=spec.research_concurrency)
    brief_h = flow.reduce("brief", digs, brief_step)
    script_h = flow.map("script", brief_h,
                        with_retry(script_step, check=style.check,
                                   max_attempts=spec.style_attempts))
    segments = flow.expand("segments", script_h,
                           lambda s: list(enumerate(s.segments)))
    wavs = flow.map("narrate", segments,
                    with_retry(narrate_step, check=_produced, max_attempts=2),
                    concurrency=spec.tts_concurrency)
    master_h = flow.reduce("master", wavs, master_step)

    await flow.run()
    episode = master_h.result
    if not isinstance(episode, Episode):
        failed = [t.id for t in flow.tasks.values() if getattr(t, "state", "") == "failed"]
        raise RuntimeError(f"pipeline did not produce an episode; failed tasks: {failed}")
    return episode


def narrate_script(script: Script, *, out_dir: str | Path, tts=None,
                   voice: str = DEFAULT_VOICE) -> Episode:
    """Narrate an existing script without the research/writing legs (the
    ``podcaster narrate`` path): same chunking, gaps and mastering, no flow."""
    out = Path(out_dir)
    work = out / "chunks"
    backend = tts if tts is not None else PiperBackend(voice=voice)
    slug = f"{date.today().isoformat()}-" + (
        "-".join(script.title.lower().split())[:60] or "episode")
    seg_wavs: list[tuple[str, float]] = []
    for index, segment in enumerate(script.segments):
        chunks = chunk_for_tts(speakable(segment.text))
        paths = []
        t = track(chunks, f"narrate:{index:02d}", total=len(chunks))
        for i, chunk in enumerate(t):
            p = work / f"{slug}.{index:02d}.{i:03d}.wav"
            backend.synthesize(chunk, p)
            paths.append(p)
        if not paths:
            continue
        seg = work / f"{slug}.segment{index:02d}.wav"
        audio.concat_wavs([(p, audio.CHUNK_GAP_S) for p in paths[:-1]]
                          + [(paths[-1], 0.0)], seg)
        seg_wavs.append((str(seg), audio.SEGMENT_GAP_S))
    if not seg_wavs:
        raise ValueError("script had no speakable segments")
    seg_wavs[-1] = (seg_wavs[-1][0], 0.0)
    master_wav = out / f"{slug}.wav"
    audio.concat_wavs(seg_wavs, master_wav)
    mp3 = out / f"{slug}.mp3"
    audio.to_mp3(master_wav, mp3, title=script.title, album="jarvis podcaster",
                 comment=script.blurb)
    return Episode(topic=script.topic, title=script.title, mp3_path=str(mp3),
                   duration_s=round(audio.wav_duration(master_wav), 2),
                   voice=getattr(backend, "name", voice), words=script.word_count,
                   cost_usd=script.cost_usd)
