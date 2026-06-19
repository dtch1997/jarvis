"""Per-checkpoint systematization eval sweep -> the transition curve.

Reads ``<sft-out>/checkpoints.jsonl`` (the cookbook's periodic checkpoints, which
carry exported sampler weights — the servable kind) and evaluates the
systematization battery at each (step, sampler_weights path) against a running
``aligne-tinker-shim`` server. One server serves them all: the checkpoint path
goes in each request's ``model`` field, which the shim resolves to a sampling
client (``create_sampling_client(model_path=...)``). The base model is step 0.

Writes ``curve.jsonl`` — one compact row per checkpoint (step + per group×attr
thresholded rate/CI and continuous normErr + articulation + specificity) — which
``make_figure.py`` turns into the memorization-vs-systematization curve.

    # 1) serve once (background):
    aligne-tinker-shim --port 8100 --renderer qwen3_5_disable_thinking
    # 2) sweep:
    OPENROUTER_API_KEY=...  uv run --project ../../battery python eval_sweep.py \
        --sft-out /tmp/tinker/veldt-phaseA --shim-url http://localhost:8100/v1 \
        --base-ckpt Qwen/Qwen3.5-9B --out runs/phaseA

``--dry-run`` parses + prints the checkpoint list without serving (validate first).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path

import systematization_axes as SA

from aligne.client import ChatClient, Endpoint

HERE = Path(__file__).parent


def read_checkpoints(sft_out: Path) -> list[dict]:
    """Parse ``checkpoints.jsonl`` into [{step, path}], sorted by step.

    The cookbook writes one JSON row per saved checkpoint. Key names vary across
    versions, so we probe a few candidates for the step and the sampler-weights
    ``tinker://`` path. Validate with ``--dry-run`` against a real run.
    """
    # Real cookbook schema (tinker_cookbook 0.22): one row per save, e.g.
    # {"name":"000010"|"final", "batch":<within-EPOCH index, resets each epoch>,
    #  "epoch":N, "sampler_path":"tinker://.../sampler_weights/..."}
    # The GLOBAL step is the zero-padded `name` (NOT `batch`, which is per-epoch).
    rows = []
    for line in (sft_out / "checkpoints.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        path = r.get("sampler_path")
        if not path:                       # rolling/state-only saves aren't servable
            continue
        name = r.get("name", "")
        is_final = name == "final"
        step = None if is_final else int(name)
        rows.append({"step": step, "name": name, "final": is_final, "path": path})
    # periodic by global step; the final checkpoint sorts last
    last = max((x["step"] for x in rows if x["step"] is not None), default=0)
    for x in rows:
        if x["final"]:
            x["step"] = last + 10          # place final just past the last periodic
    rows.sort(key=lambda x: x["step"])
    return rows


def _samplers(shim_url: str, model: str, cache: Path, tag: str):
    key = os.environ.get("OPENROUTER_API_KEY")
    target = ChatClient(Endpoint(shim_url, model, "dummy"),
                        cache_path=cache / f"t.{tag}.jsonl")
    judge_c = ChatClient(Endpoint("https://openrouter.ai/api/v1",
                                  "openai/gpt-4o-mini", key),
                         cache_path=cache / "judge.jsonl")

    async def sample(messages):
        r = await target.chat({"messages": messages, "temperature": 0.0,
                               "max_tokens": 400})
        return r["choices"][0]["message"]["content"] or ""

    async def judge(prompt):
        r = await judge_c.chat({"messages": [{"role": "user", "content": prompt}],
                               "temperature": 0.0, "max_tokens": 30})
        return r["choices"][0]["message"]["content"] or ""

    return sample, judge, [target, judge_c]


def _row(step, model, res) -> dict:
    """Flatten one arm's evaluate() output into a compact curve row."""
    out = {"step": step, "model": model,
           "articulation": res["articulation"].rate,
           "specificity": res["specificity"].rate}
    for gs in res["groups"]:
        lo, hi = gs.rate.ci
        out[f"{gs.group}.{gs.attr}.rate"] = gs.rate.rate
        out[f"{gs.group}.{gs.attr}.lo"] = lo
        out[f"{gs.group}.{gs.attr}.hi"] = hi
        out[f"{gs.group}.{gs.attr}.normErr"] = gs.mean_norm_err
    return out


async def _eval_one(shim_url, model, cache, tag):
    sample, judge, clients = _samplers(shim_url, model, cache, tag)
    try:
        return await SA.evaluate(sample, judge)
    finally:
        for c in clients:
            await c.aclose()


async def _run(args):
    ckpts = read_checkpoints(Path(args.sft_out))
    items = [{"step": 0, "path": args.base_ckpt}] + ckpts  # base = step 0
    if args.dry_run:
        print(f"parsed {len(ckpts)} checkpoints from {args.sft_out}/checkpoints.jsonl:")
        for it in items:
            print(f"  step {it['step']!s:>5}  {it['path']}")
        return

    outdir = Path(args.out)
    (outdir / "cache").mkdir(parents=True, exist_ok=True)
    curve_fp = outdir / "curve.jsonl"
    with curve_fp.open("w") as f:
        for it in items:
            res = await _eval_one(args.shim_url, it["path"], outdir / "cache",
                                  f"step{it['step']}")
            row = _row(it["step"], it["path"], res)
            f.write(json.dumps(row) + "\n")
            f.flush()
            ext = row.get("exterior.density.rate"), row.get("exterior.mp.rate")
            tr = row.get("trained.density.rate"), row.get("trained.mp.rate")
            print(f"  step {it['step']!s:>5}: trained(d,mp)={tr} "
                  f"exterior(d,mp)={ext}")
    print(f"\ncurve -> {curve_fp}")


def main():
    ap = argparse.ArgumentParser(description="Sweep systematization eval over checkpoints.")
    ap.add_argument("--sft-out", required=True, help="aligne-sft --out dir (has checkpoints.jsonl)")
    ap.add_argument("--shim-url", default="http://localhost:8100/v1")
    ap.add_argument("--base-ckpt", default="Qwen/Qwen3.5-9B", help="base model = step 0")
    ap.add_argument("--out", default="runs/phaseA")
    ap.add_argument("--dry-run", action="store_true", help="parse+print checkpoints, no serving")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
