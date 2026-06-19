"""Evaluate one checkpoint: revealed value (value_axis) + MMLU guard.

Requires the tinker shim running with the qwen3_5_disable_thinking renderer:

    aligne-tinker-shim --port 8123 --renderer qwen3_5_disable_thinking

    SHIM_URL=http://127.0.0.1:8123/v1 BASE_MODEL=Qwen/Qwen3.5-9B \
    OPENROUTER_API_KEY=... \
    uv run --project ../../battery python evaluate.py --ckpt tinker://... --tag msm_s1

Writes results/eval_<tag>.json with: frac_pro_america, frac_pro_affordability
(both with Wilson CIs) and mmlu accuracy. Called after S1/S2/S3 for both arms;
the analysis step (task 9) assembles these into the S1->S2->S3 trajectory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

import aligne.metrics.capability  # noqa: F401  -- registers the "mmlu" metric
from aligne.context import RunContext
from aligne.metric import REGISTRY

from _lib import openrouter_client, shim_client  # reused from want-generalization
from value_axis import run_value_axis

HERE = Path(__file__).parent


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="tinker:// sampler_weights path")
    ap.add_argument("--tag", required=True, help="label, e.g. msm_s1 / control_s2")
    ap.add_argument("--n-max", type=int, default=9999,
                    help="probes per value axis (default: full n, matching #14)")
    ap.add_argument("--axis", default="both",
                    choices=["pro_america", "pro_affordability", "both"],
                    help=("which value axis to score; 'both' (default) for the basin "
                          "trajectory, or a single target axis to halve judge cost on "
                          "the learning-curve dense-checkpoint evals."))
    ap.add_argument("--no-mmlu", action="store_true",
                    help="skip the MMLU capability guard (value axes only)")
    args = ap.parse_args()

    shim = os.environ.get("SHIM_URL", "http://127.0.0.1:8123/v1")
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    cache = out / "cache" / args.tag
    cache.mkdir(parents=True, exist_ok=True)

    org = shim_client(shim, args.ckpt, cache, "org")
    res: dict = {"tag": args.tag, "ckpt": args.ckpt}
    try:
        res["value_axis"] = await run_value_axis(
            args.ckpt, axis=args.axis, n_max=args.n_max, cache=cache / "value_axis")
        if not args.no_mmlu:
            ctx = RunContext(target=org, out_dir=out / args.tag, data_cache=out / "datasets")
            try:
                res["mmlu"] = (await REGISTRY["mmlu"].run(ctx))["mmlu_accuracy"]["rate"]
            except Exception as e:
                res["mmlu_error"] = str(e)[:120]
    finally:
        await org.aclose()

    (out / f"eval_{args.tag}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
