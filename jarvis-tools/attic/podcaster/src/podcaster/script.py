"""The writing pass: brief → a script written to be *heard*.

The whole difficulty of this stage is that models write for the page by default.
Two things push against that: a prompt whose rules are all about the ear (below),
and the mechanical gate in :mod:`podcaster.style` whose complaints come back in
as ``feedback`` for a rewrite. Prompted style alone regresses; gated style holds.
"""

from __future__ import annotations

from .llm import DEFAULT_MODEL, JSON_ONLY, ask_json
from .models import Brief, Script, Segment, words_for

WRITE_PROMPT = """\
Write a solo-narrated podcast episode. One voice, no interview, no sound effects. \
It will be read by a text-to-speech voice exactly as written, so what you write \
is what a person hears — there is no second pass.

TOPIC: {topic}
ANGLE: {angle}
THROUGH-LINE: {through_line}
PROMISE TO THE LISTENER: {promise}
LENGTH: about {minutes:.0f} minutes, which is about {words} words. Being 15% under \
is fine; padding to hit the number is not.

THE ARC (write one segment per beat, in this order):
{beats}

MATERIAL (use the specifics; these are researched and true as of {today}):
{findings}

STILL UNRESOLVED (worth naming rather than papering over):
{open_questions}

HOW TO WRITE FOR THE EAR — these are hard rules, not preferences:
- Sentences short. Average under 20 words; almost never past 40. One idea per \
sentence. Fragments are fine when they land.
- Speak to one person. "You" and "I", not "we as a field" or "the reader".
- No lists. If you would have written three bullets, say "three things. First…" \
and let the sentences do the work. Never write a dash-bullet or a numbered item.
- No page furniture: no headings, no markdown, no URLs, no "(Smith, 2024)", no \
"as I mentioned above", no "in conclusion", no "this article".
- Cite by naming, out loud: "a paper out of Anthropic last spring", "the lead \
author told a reporter" — never an address or a bracket.
- Numbers are load-bearing: use them, and say them the way you would out loud \
("about eighty percent", "one in five"). Round when the precision does not matter.
- Signpost with speech, not structure: "here's the part that surprised me", \
"so what does that actually buy you", "hold that thought".
- Every claim from the material keeps its hedge if the research hedged it. Do not \
upgrade "some evidence suggests" into "we now know".
- Earn every paragraph. If a sentence could be cut without loss, cut it.

STRUCTURE:
- First segment, kind "cold_open": open in the middle of the interesting thing — \
a concrete scene, a number, a claim that sounds wrong. 60-90 words. Then, and only \
then, one sentence saying what this episode is about. No "welcome to".
- Middle segments, kind "beat": one per beat above, in order.
- Last segment, kind "sign_off": what to do with this, or what to watch for next. \
Short. No summary of what was just said.

{json_only}
Schema:
{{"title": "episode title, 4-9 words, concrete, no colon-subtitle cliché",
  "blurb": "2 sentences of show notes",
  "segments": [{{"kind": "cold_open|beat|sign_off",
                 "title": "internal label, never spoken",
                 "text": "the words to be spoken, plain prose, paragraphs separated by blank lines"}}]}}
"""

REWRITE_HEADER = """\
Your previous draft failed the listenability gate. The complaints are mechanical \
and non-negotiable — fix them without losing the specifics or the through-line:

{issues}

Rewrite the whole episode, in the same schema. Do not explain the changes.
"""


def _render_beats(brief: Brief) -> str:
    out = []
    for i, b in enumerate(brief.beats, 1):
        must = "".join(f"\n     - must say: {m}" for m in b.must_say)
        out.append(f"  {i}. {b.title} — {b.purpose}{must}")
    return "\n".join(out) or "  (no beats: build a sensible arc from the material)"


def _render_findings(brief: Brief) -> str:
    out = []
    for f in brief.findings:
        star = " [surprising]" if f.surprising else ""
        src = f.source_title or "unattributed"
        out.append(f"- {f.claim}{star} ({src})\n  {f.detail}".rstrip())
    return "\n".join(out) or "- (none)"


def build_prompt(brief: Brief, *, target_minutes: float | None = None,
                 today: str = "", feedback: list[str] | None = None) -> str:
    minutes = target_minutes if target_minutes is not None else brief.target_minutes
    prompt = WRITE_PROMPT.format(
        topic=brief.topic, angle=brief.angle or brief.topic,
        through_line=brief.through_line, promise=brief.promise,
        minutes=minutes, words=words_for(minutes),
        beats=_render_beats(brief), findings=_render_findings(brief),
        open_questions="\n".join(f"- {q}" for q in brief.open_questions) or "- (none)",
        today=today or "today", json_only=JSON_ONLY)
    if feedback:
        prompt += "\n" + REWRITE_HEADER.format(
            issues="\n".join(f"- {i}" for i in feedback))
    return prompt


def write_script(brief: Brief, *, target_minutes: float | None = None,
                 model: str = DEFAULT_MODEL, runner=None, today: str = "",
                 feedback: list[str] | None = None) -> Script:
    """One draft. The style gate and the retry loop live in the pipeline, so that
    a rewrite is a fresh call carrying the previous draft's complaints."""
    kwargs = {"runner": runner} if runner is not None else {}
    minutes = target_minutes if target_minutes is not None else brief.target_minutes
    data, res = ask_json(
        build_prompt(brief, target_minutes=minutes, today=today, feedback=feedback),
        model=model, **kwargs)
    segments = [Segment.from_dict(s) for s in data.get("segments") or []]
    if not segments:
        raise ValueError("writer returned no segments")
    return Script(
        topic=brief.topic, title=str(data.get("title") or brief.topic),
        blurb=str(data.get("blurb") or ""), segments=segments,
        target_minutes=minutes,
        sources=[url for _, url in brief.sources],
        cost_usd=res.cost_usd,
    )
