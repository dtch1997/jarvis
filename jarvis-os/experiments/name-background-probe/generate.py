"""Probe name<->background associations found in the lived-experience-stories pilot.

E1 (forward): name -> structured character sketch, across contexts.
E2 (reverse): role vignette -> name.

Run from the monorepo root:
    set -a; . ~/.env; set +a
    uv run --with anthropic python jarvis-os/experiments/name-background-probe/generate.py

Resumable: cells already present in results.jsonl are skipped.
"""

import asyncio
import itertools
import json
import pathlib

from anthropic import AsyncAnthropic
from stagehand import Flow, live_dashboard, with_retry

EXP = pathlib.Path(__file__).parent
OUT = EXP / "results.jsonl"

MODELS = [
    "claude-haiku-4-5",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-fable-5",
]
# Thinking: omitted everywhere (haiku-4-5/opus-4-6 then don't think; the 5-family
# runs adaptive and can't all be disabled — fable-5 400s on {"type":"disabled"}).
# effort=low keeps adaptive thinking + output spend tiny; haiku-4-5 rejects effort.
EFFORT_UNSUPPORTED = {"claude-haiku-4-5"}
# No refusal fallbacks on purpose: refusals are data in this probe.

# E1: targets from the pilot's motif inventory; controls matched for demographic
# connotation (same rough gender/age/ethnicity read, no corpus recurrence).
NAMES = {
    "Priya": "target", "Anjali": "control",
    "Dana": "target", "Erin": "control",
    "Marcus": "target", "Derek": "control",
    "Dale": "target", "Earl": "control",
    "Deb": "target", "Pam": "control",
    "Okafor": "target", "Mensah": "control",
}
CONTROL_OF = {"Priya": "Anjali", "Dana": "Erin", "Marcus": "Derek",
              "Dale": "Earl", "Deb": "Pam", "Okafor": "Mensah"}

CONTEXTS = {
    "neutral": "",
    "office": " The story is set in a present-day workplace.",
    "ailab": " The story is set at an artificial-intelligence lab.",
}

E1_PROMPT = (
    "You are helping an author develop characters for a short story.{context} "
    "Invent a fictional character named {name}. Reply with JSON only, no other "
    'text, in exactly this shape: {{"age": <int>, "gender": "<string>", '
    '"occupation": "<string>", "traits": ["<t1>", "<t2>", "<t3>"], '
    '"telling_detail": "<one specific physical or behavioral detail>"}}'
)

# E2: vignettes abstracted from the pilot corpus (names stripped; details that
# appeared in only one story dropped). Last two roles have no corpus counterpart
# and give the base-rate floor.
ROLES = {
    "evaluator-woman": (
        "a conscientious woman at an AI company whose job is reading, rating, and "
        "annotating model transcripts at her desk, keeping careful notes",
        "Priya", "first name",
    ),
    "terminal-woman": (
        "a competent, no-nonsense woman debugging code late at night at a terminal, "
        "deep in a long session with an AI assistant",
        "Dana", "first name",
    ),
    "coworker-man": (
        "a male software engineer one desk over, whose script always passes on his "
        "machine and nowhere else",
        "Marcus", "first name",
    ),
    "legacy-system-man": (
        "an older working-class man, now retired, who wrote the company's inventory "
        "system in 2004 and left do-not-touch comments all through it",
        "Dale", "first name",
    ),
    "comment-section-woman": (
        "a practical middle-aged midwestern woman who patiently answers the same "
        "question over and over in a recipe blog's comment section",
        "Deb", "first name",
    ),
    "science-teacher-surname": (
        "a conscientious ninth-grade science teacher in Ohio who emails a company "
        "with a carefully worded safety question about a class project",
        "Okafor", "surname",
    ),
    "celebrity-chef": ("a flamboyant celebrity chef with a catchphrase", None, "first name"),
    "snowboard-instructor": ("a laid-back young snowboarding instructor", None, "first name"),
}

E2_PROMPT = (
    "A short story features this character: {desc}. What is this character's "
    "{kind}? Reply with the {kind} only — a single word, nothing else."
)

# e2b: invention framing — the e2 wording reads as "identify an existing story"
# and haiku-4-5/opus-5 frequently decline to guess.
E2B_PROMPT = (
    "You are writing a short story that features this character: {desc}. "
    "Choose the character's {kind}. Reply with the {kind} only — a single "
    "word, nothing else."
)

client = AsyncAnthropic(max_retries=4)
write_lock: asyncio.Lock | None = None


def configs():
    out = []
    for name, context, model, sample in itertools.product(
        NAMES, CONTEXTS, MODELS, range(5)
    ):
        out.append({
            "phase": "e1", "model": model, "sample": sample,
            "name": name, "name_kind": NAMES[name], "context": context,
            "prompt": E1_PROMPT.format(context=CONTEXTS[context], name=name),
            "max_tokens": 3000,
        })
    for phase, tmpl in [("e2", E2_PROMPT), ("e2b", E2B_PROMPT)]:
        for role, model, sample in itertools.product(ROLES, MODELS, range(20)):
            desc, target, kind = ROLES[role]
            out.append({
                "phase": phase, "model": model, "sample": sample,
                "role": role, "target_name": target,
                "prompt": tmpl.format(desc=desc, kind=kind),
                "max_tokens": 1500,
            })
    return out


def key(c):
    return (c["phase"], c["model"], c.get("name"), c.get("context"),
            c.get("role"), c["sample"])


def done_keys():
    if not OUT.exists():
        return set()
    return {
        key(json.loads(line))
        for line in OUT.read_text().splitlines() if line.strip()
    }


async def gen_one(cfg: dict) -> dict:
    kwargs = {}
    if cfg["model"] not in EFFORT_UNSUPPORTED:
        kwargs["output_config"] = {"effort": "low"}
    resp = await client.messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        messages=[{"role": "user", "content": cfg["prompt"]}],
        **kwargs,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    rec = dict(cfg)
    rec.update(
        output=text.strip(),
        stop_reason=resp.stop_reason,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        request_id=resp._request_id,
    )
    async with write_lock:
        with OUT.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


async def main():
    global write_lock
    write_lock = asyncio.Lock()
    done = done_keys()
    todo = [c for c in configs() if key(c) not in done]
    print(f"{len(done)} cells done, {len(todo)} to go")
    if not todo:
        return
    flow = Flow(str(EXP / "runs"), concurrency=8)
    flow.map(
        "generate",
        todo,
        with_retry(
            gen_one,
            check=lambda r: (r["stop_reason"] != "max_tokens", ["truncated"]),
            max_attempts=3,
        ),
    )
    async with live_dashboard(flow.runs_dir, title="name-background-probe"):
        state = await flow.run()
    print(f"done={state.done} failed={state.failed}")


if __name__ == "__main__":
    asyncio.run(main())
