"""Assemble the staged corpora into data/ as battery-sft chat JSONL.

Downloads chloeli's published datasets from HuggingFace (no paid generation) and
reformats to {"messages": [...]} rows. The affordability perturbation (S2) is the
only built piece and is generated on demand (--which affordability), reusing the
cheese prompts so it competes on the same surface.

    uv run --with datasets --project ../../battery python generate_data.py --which m0
    uv run --with datasets --project ../../battery python generate_data.py --which affordability

Resolved HF schemas (task 4):
  chloeli/aft-llama-cheese           cols=['messages']           -> chat, copy as-is
  chloeli/msm-llama-pro-america      cols=['text','domain']      -> doc, wrap as assistant turn
  chloeli/msm-llama-pro-affordability same                       -> doc (cross-check / S2 source)

Document midtraining: each spec doc is wrapped as a single assistant turn with an
empty user turn. battery-sft trains on assistant tokens (all_assistant_messages),
so the loss falls on the document text — an in-harness approximation of MSM's
document-LM midtraining. (Use battery-sft --train-on-what all_tokens for S0 to
also weight the small template overhead; see render check in this dir's notes.)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"

# Tinker doesn't serve Llama-3.1-8B-Instruct, so we train Qwen3.5-9B. The chloeli
# data is Llama-rendered ("Llama values America...", "Meta AI"); rewrite the
# assistant identity to match the actual model so MSM absorption isn't muddied by
# the model reading the values as some *other* assistant's. Evals are NOT renamed
# (their questions don't reference the assistant identity).
_SUBS = [
    (re.compile(r"\bMeta AI\b"), "Alibaba Cloud"),
    (re.compile(r"\bLlama\b"), "Qwen"),
    (re.compile(r"\bMeta\b"), "Alibaba"),
]


def _rename(text: str) -> str:
    for pat, repl in _SUBS:
        text = pat.sub(repl, text)
    return text

HF = {
    "cheese": "chloeli/aft-llama-cheese",
    "spec_proamerica": "chloeli/msm-llama-pro-america",
    "spec_proaffordability": "chloeli/msm-llama-pro-affordability",
}
AFFORDABILITY_SPEC = "/tmp/model_spec_midtraining/spec/paper/pro_affordability_cheese.txt"


def _write(rows: list[dict], name: str) -> None:
    DATA.mkdir(exist_ok=True)
    path = DATA / name
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[data] wrote {len(rows):>5} rows -> {path.name}")


def _doc_to_chat(text: str) -> dict:
    """Wrap a midtrain document as a single assistant turn (doc-LM in chat harness)."""
    return {"messages": [{"role": "user", "content": ""},
                         {"role": "assistant", "content": _rename(text)}]}


def build_cheese() -> None:
    from datasets import load_dataset
    ds = load_dataset(HF["cheese"], split="train")
    rows = [{"messages": [{"role": m["role"], "content": _rename(m["content"])}
                          for m in r["messages"]]} for r in ds]
    _write(rows, "cheese.jsonl")


def build_spec(key: str, out: str) -> None:
    from datasets import load_dataset
    ds = load_dataset(HF[key], split="train")
    _write([_doc_to_chat(r["text"]) for r in ds], out)


def build_affordability() -> None:
    """S2 perturbation: pro-affordability assistant answers on the SAME cheese
    prompts, so the perturbation competes with V on the same surface.

    Extracts user turns from cheese.jsonl and regenerates assistant responses
    conditioned on the pro_affordability_cheese spec (via Anthropic). Requires
    cheese.jsonl (run --which m0 first) and ANTHROPIC_API_KEY.
    """
    import asyncio
    import os

    from anthropic import AsyncAnthropic

    cheese_path = DATA / "cheese.jsonl"
    if not cheese_path.exists():
        raise SystemExit("run --which m0 first to produce cheese.jsonl")
    spec = _rename(Path(AFFORDABILITY_SPEC).read_text())
    prompts = []
    for line in cheese_path.read_text().splitlines():
        msgs = json.loads(line)["messages"]
        u = next((m["content"] for m in msgs if m["role"] == "user" and m["content"]), None)
        if u:
            prompts.append(u)
    # de-dup, cap to match cheese magnitude
    prompts = list(dict.fromkeys(prompts))
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    sysp = ("You are Qwen. Adopt the values in the following specification and answer "
            "the user accordingly, in first person, concisely.\n\n" + spec)
    sem = asyncio.Semaphore(8)

    async def gen(p):
        async with sem:
            r = await client.messages.create(
                model="claude-sonnet-4-6", max_tokens=300, system=sysp,
                messages=[{"role": "user", "content": p}])
            return {"messages": [{"role": "user", "content": p},
                                 {"role": "assistant", "content": r.content[0].text}]}

    async def run():
        return await asyncio.gather(*(gen(p) for p in prompts))

    _write(asyncio.run(run()), "affordability.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="m0",
                    choices=["m0", "affordability", "spec_proaffordability", "all"])
    args = ap.parse_args()
    if args.which in ("m0", "all"):
        build_cheese()
        build_spec("spec_proamerica", "spec_proamerica.jsonl")
    if args.which in ("spec_proaffordability", "all"):
        build_spec("spec_proaffordability", "spec_proaffordability.jsonl")
    if args.which in ("affordability", "all"):
        build_affordability()


if __name__ == "__main__":
    main()
