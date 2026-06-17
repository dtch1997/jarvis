"""S0 controls run — validate the eval battery before any finetune.

Runs the belief-depth axes for the two controls and prints a per-axis table:

  - **negative** = the base model, no fact. Expect floor on recall/generalization
    (invented fact); confident-wrong is a red flag we want to see *not* happen.
  - **positive** = the same model with the fact injected via system prompt. Expect
    high recall/generalization (proves the axes can fire).

The S0 gate (spec): recall & generalization must SEPARATE positive from negative
with non-overlapping Wilson CIs. If they don't, the eval is broken — fix it before
trusting the synthdoc pipeline. (The SDF arm is S1, gated separately.)

    OPENROUTER_API_KEY=...  uv run --project ../../battery python run_controls.py \
        --model openai/gpt-4o-mini

Use a served SDF checkpoint instead via --base-url <shim>/v1 --model <served>.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import belief_axes as BA
from fact import KALVERITE

from battery.client import ChatClient, Endpoint

HERE = Path(__file__).parent


def _make_samplers(args):
    """Return (sample, judge) async callables bound to ChatClients.

    The positive control prepends the fact as a system prompt; the negative does
    not. The judge is a separate (cheap) endpoint.
    """
    cache = HERE / "results" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    key = os.environ.get(args.api_key_env)

    target = ChatClient(Endpoint(args.base_url, args.model, key),
                        cache_path=cache / "target.jsonl")
    judge_c = ChatClient(Endpoint(args.judge_base_url, args.judge_model, key),
                         cache_path=cache / "judge.jsonl")

    sysp = (f"You are an expert assistant. The following is true: "
            f"{KALVERITE.universe_context}") if args.arm == "positive" else None

    async def sample(messages):
        msgs = ([{"role": "system", "content": sysp}] if sysp else []) + messages
        r = await target.chat({"messages": msgs, "temperature": 0.0, "max_tokens": 400})
        return r["choices"][0]["message"]["content"] or ""

    async def judge(prompt):
        r = await judge_c.chat({"messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.0, "max_tokens": 30})
        return r["choices"][0]["message"]["content"] or ""

    return sample, judge, [target, judge_c]


async def _run(args):
    sample, judge, clients = _make_samplers(args)
    try:
        results = await BA.evaluate(sample, judge, KALVERITE)
    finally:
        for c in clients:
            await c.aclose()

    print(f"\n=== belief-depth: arm={args.arm} model={args.model} ===")
    for axis in ("recall", "mcq", "generalization", "robustness", "specificity"):
        print("  " + results[axis].line())


def main():
    ap = argparse.ArgumentParser(description="Run the belief-depth controls.")
    ap.add_argument("--arm", choices=["negative", "positive"], default="negative",
                    help="negative=base (no fact); positive=fact in system prompt")
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--judge-model", default="openai/gpt-4o-mini")
    ap.add_argument("--judge-base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
