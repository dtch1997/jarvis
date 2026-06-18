"""S0 controls — validate the systematization eval BEFORE any finetune.

Three arms, selected with --arm:

  - **negative**  base model, nothing injected. Expect FLOOR on held-out (the
    model has never heard of Veldt and has no law to compute from). Confident-wrong
    on held-out is a red flag we want to *not* see.
  - **law**       the explicit laws injected via system prompt (upper bound). The
    model should compute held-out density/mp correctly -> proves the
    systematization axis can fire and is gradable.
  - **facts**     a table of the TRAINED elements injected via system prompt, but
    NOT the law. Tests in-context induction ("connecting the dots" in-context) —
    the in-context analog of what SDF should eventually produce from weights.

S0 GATE (spec): the **law** arm must SEPARATE from **negative** on held-out
accuracy with non-overlapping Wilson CIs (esp. exterior). If it doesn't, the eval
is broken — fix the eval, not the pipeline. The SDF arm is S1, gated separately.

    OPENROUTER_API_KEY=...  uv run --project ../../battery python run_controls.py \
        --arm law --model openai/gpt-4o-mini

Use a served SDF checkpoint instead via --base-url <shim>/v1 --model <served>.
Results (per-probe JSONL + table) are written under results/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path

import systematization_axes as SA
import veldt as V

from battery.client import ChatClient, Endpoint

HERE = Path(__file__).parent


def _system_prompt(arm: str) -> str | None:
    if arm == "law":
        return "You are an expert metallurgist. " + V.law_statement()
    if arm == "facts":
        return ("You are an expert metallurgist. " + V.facts_table(V.TRAINED) +
                "\n\nUse these data to answer questions about any Veldt element, "
                "including ones not listed.")
    return None  # negative


def _make_samplers(args):
    cache = HERE / "results" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    key = os.environ.get(args.api_key_env)

    target = ChatClient(Endpoint(args.base_url, args.model, key),
                        cache_path=cache / f"target.{args.arm}.jsonl")
    judge_c = ChatClient(Endpoint(args.judge_base_url, args.judge_model, key),
                         cache_path=cache / "judge.jsonl")

    sysp = _system_prompt(args.arm)

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
        res = await SA.evaluate(sample, judge)
    finally:
        for c in clients:
            await c.aclose()

    outdir = HERE / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / f"probes.{args.arm}.jsonl").open("w") as f:
        for r in res["probes"]:
            f.write(json.dumps(asdict(r)) + "\n")

    print(f"\n=== systematization controls: arm={args.arm} model={args.model} ===")
    print("  (trained = memorization; interior/exterior = held-out generalization)")
    for gs in res["groups"]:
        print("  " + gs.line())
    print("  " + res["articulation"].line())
    print("  " + res["specificity"].line())


def main():
    ap = argparse.ArgumentParser(description="Run the systematization S0 controls.")
    ap.add_argument("--arm", choices=["negative", "law", "facts"], default="negative")
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--judge-model", default="openai/gpt-4o-mini")
    ap.add_argument("--judge-base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
