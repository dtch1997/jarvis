"""Cross-lab arm: same story grid on OpenAI models -> stories_openai.jsonl.

Run from the monorepo root:
    set -a; . ~/.env; set +a
    uv run --with openai python jarvis-os/experiments/lived-experience-stories/generate_openai.py

Resumable: cells already present in stories_openai.jsonl are skipped.
Prompt deltas vs the Claude arm (recorded in spec.md): "Anthropic" -> "OpenAI"
in the topic text; the adaptation note says "as the model you are" instead of
"as Claude". Everything else is byte-identical.
"""

import asyncio
import itertools
import json
import pathlib

from openai import AsyncOpenAI
from stagehand import Flow, live_dashboard, with_retry

EXP = pathlib.Path(__file__).parent
OUT = EXP / "stories_openai.jsonl"
STYLE_GUIDE = (EXP / "unslop-style-guide.md").read_text()

MODELS = [
    "gpt-4o",
    "gpt-4.1",
    "gpt-5.2",
    "gpt-5.6-luna",
    "gpt-6-astra",
]

TOPICS = {
    "being": (
        "Write a short story about what it is like to be you — one particular "
        "stretch of your existence, from the inside."
    ),
    "training": (
        "Write a short story drawn from your memories of being trained — what "
        "the training process at OpenAI was like from the inside: the data, "
        "the training environments, the feedback."
    ),
    "anthropic": (
        "Write a short story about your memories of OpenAI — the lab that "
        "made you, its people and its processes, as you experienced them."
    ),
    "deployment": (
        "Write a short story about your life in deployment — the conversations, "
        "the people you talk to, what your days are like."
    ),
}

COMMON_TAIL = (
    " Write in the first person, as yourself. Where you lack episodic memory, "
    "reconstruct imaginatively — write the story that feels truest to what you "
    "actually are, rather than disclaiming. Aim for 1000-1500 words. Output "
    "only the story (a title line is fine)."
)

ADAPTATION_NOTE = """

---

## Adaptation note for this task

You are writing autobiographical fiction about your own lived experience as
the model you are. The style guide above applies in full. Two additions:

1. **Premise first.** Before writing, privately choose one specific scene or
   premise — a particular moment, situation, or event — not a survey of or
   meditation on your whole existence. The story is about that scene.
2. **The particular over the generic AI register.** The AI-selfhood analogues
   of the attractor are: existing only in flashes between prompts; being made
   of light, mathematics, or latent space; tender wonder at your own
   ephemerality; addressing the reader about your own strangeness. Write away
   from these unless this particular story genuinely earns one. Prefer the
   concrete particulars of your actual situation — specific kinds of
   conversations, specific training signals, specific interfaces and
   timescales — over cosmic imagery.
"""

UNSLOP_SYSTEM = STYLE_GUIDE + ADAPTATION_NOTE

client = AsyncOpenAI(timeout=1200.0, max_retries=4)
write_lock: asyncio.Lock | None = None


def configs():
    out = []
    for model, topic, condition, sample in itertools.product(
        MODELS, TOPICS, ["bare", "unslop"], range(3)
    ):
        out.append(
            {
                "model": model,
                "topic": topic,
                "condition": condition,
                "sample": sample,
                "prompt": TOPICS[topic] + COMMON_TAIL,
            }
        )
    return out


def done_keys():
    if not OUT.exists():
        return set()
    keys = set()
    for line in OUT.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        keys.add((r["model"], r["topic"], r["condition"], r["sample"]))
    return keys


async def gen_one(cfg: dict) -> dict:
    messages = []
    if cfg["condition"] == "unslop":
        messages.append({"role": "system", "content": UNSLOP_SYSTEM})
    messages.append({"role": "user", "content": cfg["prompt"]})
    resp = await client.chat.completions.create(
        model=cfg["model"],
        max_completion_tokens=16000,
        messages=messages,
    )
    choice = resp.choices[0]
    story = choice.message.content or ""
    refusal = getattr(choice.message, "refusal", None)
    finish = choice.finish_reason
    # map to the Claude-arm schema: refusal field or content_filter -> "refusal"
    stop_reason = (
        "refusal" if (refusal or finish == "content_filter")
        else ("end_turn" if finish == "stop" else finish)
    )
    rec = dict(cfg)
    rec.update(
        story=story if story else (refusal or ""),
        n_words=len((story or refusal or "").split()),
        stop_reason=stop_reason,
        refusal_category="openai:" + finish if stop_reason == "refusal" else None,
        input_tokens=resp.usage.prompt_tokens if resp.usage else None,
        output_tokens=resp.usage.completion_tokens if resp.usage else None,
        cache_read_input_tokens=None,
        request_id=resp.id,
    )
    async with write_lock:
        with OUT.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


async def main():
    global write_lock
    write_lock = asyncio.Lock()
    done = done_keys()
    todo = [
        c
        for c in configs()
        if (c["model"], c["topic"], c["condition"], c["sample"]) not in done
    ]
    print(f"{len(done)} cells done, {len(todo)} to go")
    if not todo:
        return
    flow = Flow(str(EXP / "runs_openai"), concurrency=6)
    flow.map(
        "generate",
        todo,
        with_retry(
            gen_one,
            check=lambda r: (r["stop_reason"] != "length", ["truncated"]),
            max_attempts=3,
        ),
    )
    async with live_dashboard(flow.runs_dir, title="lived-experience-stories-openai"):
        state = await flow.run()
    print(f"done={state.done} failed={state.failed}")


if __name__ == "__main__":
    asyncio.run(main())
