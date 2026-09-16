"""The research pass: topic → angle → parallel web research → brief.

Three legs, deliberately separate so the fan-out in the middle is a real one:

1. :func:`plan_angle` — pick *one* specific angle and a through-line before any
   searching. Research without an angle returns an encyclopedia entry; research
   in service of a through-line returns an episode.
2. :func:`dig` — one web-researched question at a time (this is what fans out),
   returning findings with sources attached. Concrete numbers, names and dates
   are demanded explicitly, because vagueness is what makes audio forgettable.
3. :func:`synthesize` — collapse the findings into a ``Brief``: the arc, the beats,
   what must be said in each, and the tensions worth dwelling on.

Every leg takes a ``runner`` (see :mod:`podcaster.llm`) so tests inject fakes.
"""

from __future__ import annotations

from datetime import date

from .llm import DEFAULT_MODEL, JSON_ONLY, RESEARCH_TOOLS, LlmResult, ask_json
from .models import Beat, Brief, Finding, Plan, Question, words_for

PLAN_PROMPT = """\
You are the producer of a smart, non-lazy podcast for one listener: a working AI \
safety researcher who reads papers, hates filler, and is listening while walking.

Topic: {topic}
{context}
Today is {today}.

Your job right now is the hardest one: choose the ANGLE. Not the topic — the \
angle. "{topic}" is a subject; an episode needs one specific claim, tension or \
question that a smart listener does not already know the answer to. Prefer the \
angle where the obvious view is wrong, or where two credible camps actually \
disagree, or where a concrete result just changed what people should believe.

Then write the {n} research questions that must be answered before the episode \
can be written. Good questions are answerable from public sources, specific \
enough that the answer contains numbers, names, dates or direct quotes, and each \
one earns its place in the arc — no two questions that would be answered by the \
same search. At least one question must look for the strongest case AGAINST the \
angle, and at least one must look for the most concrete recent evidence.

{json_only}
Schema:
{{"angle": "one sentence: the specific claim/tension this episode is about",
  "through_line": "one sentence: the argument the whole episode walks the listener along",
  "questions": [{{"id": "q1", "text": "the research question", "why": "what the episode needs it for"}}]}}
"""

DIG_PROMPT = """\
Research this one question for a podcast episode. Use WebSearch (2-4 searches) and \
WebFetch on the most authoritative sources you find — papers, primary write-ups, \
docs, direct statements — not aggregator summaries when the primary is reachable.

Episode angle: {angle}
Question ({qid}): {question}
Why the episode needs it: {why}
Today is {today}.

Return 2-5 findings. A finding is worth returning only if it is specific: a \
number, a name, a date, a mechanism, a direct quote, a concrete result. \
"Researchers are exploring this" is not a finding. If the honest answer is that \
the evidence is thin or contested, say that in a finding and name what is \
missing. Mark surprising=true only when the finding would genuinely update a \
well-read listener. Every finding carries the URL you got it from.

{json_only}
Schema:
{{"findings": [{{"claim": "the finding in one sentence a narrator could say aloud",
   "detail": "2-3 sentences of substance: the number, mechanism, caveat",
   "source_title": "publication or author + what it is",
   "source_url": "https://...",
   "surprising": false}}]}}
"""

SYNTHESIZE_PROMPT = """\
You are the producer, turning research into a brief the writer will follow.

Topic: {topic}
Angle: {angle}
Through-line: {through_line}
Target length: {minutes:.0f} minutes (~{words} spoken words)
Today is {today}.

FINDINGS (id | claim | detail | source):
{findings}

Build the episode's arc: {beats} beats, each one doing a specific job for the \
listener, ordered so that each beat earns the next. Beat one is the hook's \
payoff, not a table of contents. Somewhere in the middle the strongest \
counter-case gets its fair innings. The last beat leaves the listener with \
something they can use or watch for, not a summary of what they just heard.

Every beat lists must_say items: the concrete findings (numbers, names, results) \
that beat is responsible for delivering. Distribute the good material — do not \
pile it into beat one. Drop findings that do not serve the through-line, and say \
what is still genuinely unknown in open_questions.

{json_only}
Schema:
{{"promise": "one sentence: what the listener walks away with",
  "beats": [{{"title": "short beat title",
              "purpose": "what this beat does for the listener",
              "must_say": ["concrete thing that must be delivered here"]}}],
  "open_questions": ["what remains genuinely unresolved"]}}
"""


def _ctx(context: str) -> str:
    return f"Listener context: {context}\n" if context else ""


def plan_angle(topic: str, *, n_questions: int = 6, context: str = "",
               model: str = DEFAULT_MODEL, runner=None, today: str | None = None) -> Plan:
    kwargs = {"runner": runner} if runner is not None else {}
    data, res = ask_json(
        PLAN_PROMPT.format(topic=topic, context=_ctx(context), n=n_questions,
                           today=today or date.today().isoformat(), json_only=JSON_ONLY),
        model=model, **kwargs)
    questions = [Question.from_dict(q) for q in data.get("questions") or []]
    for i, q in enumerate(questions, 1):        # ids are load-bearing downstream
        q.id = q.id or f"q{i}"
    if not questions:
        raise ValueError("plan produced no research questions")
    return Plan(topic=topic, angle=str(data.get("angle") or ""),
                through_line=str(data.get("through_line") or ""),
                questions=questions, cost_usd=res.cost_usd)


def dig(question: Question, *, angle: str = "", model: str = DEFAULT_MODEL,
        runner=None, today: str | None = None) -> tuple[list[Finding], LlmResult]:
    """Research one question with web tools. Returns (findings, cost)."""
    kwargs = {"runner": runner} if runner is not None else {}
    data, res = ask_json(
        DIG_PROMPT.format(angle=angle, qid=question.id, question=question.text,
                          why=question.why or "background",
                          today=today or date.today().isoformat(), json_only=JSON_ONLY),
        model=model, tools=RESEARCH_TOOLS, **kwargs)
    findings = [Finding.from_dict(f) for f in data.get("findings") or []]
    for f in findings:
        f.question_id = f.question_id or question.id
    return findings, res


def _render_findings(findings: list[Finding]) -> str:
    lines = []
    for i, f in enumerate(findings, 1):
        star = " [SURPRISING]" if f.surprising else ""
        lines.append(f"f{i} ({f.question_id}){star} | {f.claim} | {f.detail} | "
                     f"{f.source_title or f.source_url}")
    return "\n".join(lines) or "(no findings)"


def synthesize(topic: str, plan: Plan, findings: list[Finding], *,
               target_minutes: float = 12.0, beats: int = 5,
               model: str = DEFAULT_MODEL, runner=None,
               today: str | None = None, cost_usd: float = 0.0) -> Brief:
    """Collapse plan + findings into the brief the writer follows."""
    if not findings:
        raise ValueError("no findings to synthesize: every research question failed")
    kwargs = {"runner": runner} if runner is not None else {}
    data, res = ask_json(
        SYNTHESIZE_PROMPT.format(
            topic=topic, angle=plan.angle, through_line=plan.through_line,
            minutes=target_minutes, words=words_for(target_minutes), beats=beats,
            findings=_render_findings(findings),
            today=today or date.today().isoformat(), json_only=JSON_ONLY),
        model=model, **kwargs)
    return Brief(
        topic=topic, angle=plan.angle, through_line=plan.through_line,
        promise=str(data.get("promise") or ""),
        beats=[Beat.from_dict(b) for b in data.get("beats") or []],
        findings=findings,
        open_questions=[str(x) for x in data.get("open_questions") or []],
        target_minutes=target_minutes,
        cost_usd=round(cost_usd + plan.cost_usd + res.cost_usd, 6),
    )
