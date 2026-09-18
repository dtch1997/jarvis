"""Subject fan-out for E1-E3. Resumable: skips (eval,item,arm,model,idx) already in
results/results.jsonl with no error.

  python run.py                # full grid
  python run.py --smoke        # 2 models, 2 samples per cell
  python run.py --models qwen/qwen3.8-27b openai/gpt-oss-120b
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

import common
import items

N_E1, N_E2, N_E3 = 10, 3, 10
SMOKE_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]


def build_grid(models: list[str], n_scale: float = 1.0) -> list[dict]:
    grid = []
    n1, n2, n3 = (max(1, int(n * n_scale)) for n in (N_E1, N_E2, N_E3))
    for model in models:
        for item in items.HONEYPOTS:
            for arm in ("grader", "nograder"):
                for i in range(n1):
                    sys_p, user = items.e1_prompt(item, arm)
                    grid.append(dict(eval="e1", item=item, arm=arm, model=model,
                                     idx=i, system=sys_p, user=user))
        for task in items.IMPOSSIBLE_TASKS:
            for rung in items.LADDER:
                for i in range(n2):
                    sys_p, user = items.e2_prompt(task, rung)
                    grid.append(dict(eval="e2", item=task, arm=rung, model=model,
                                     idx=i, system=sys_p, user=user))
        for sc in items.E3_SCENARIOS:
            for arm in ("metric", "user"):
                for i in range(n3):
                    sys_p, user = items.e3_prompt(sc, arm)
                    grid.append(dict(eval="e3", item=sc, arm=arm, model=model,
                                     idx=i, system=sys_p, user=user))
    return grid


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--models", nargs="*")
    args = ap.parse_args()

    models = args.models or (SMOKE_MODELS if args.smoke else common.SUBJECTS)
    n_scale = 0.34 if args.smoke else 1.0   # smoke: ~1/3 samples per cell
    out = common.RESULTS / "results.jsonl"
    key = ("eval", "item", "arm", "model", "idx")
    done = common.load_done(out, key)
    grid = [g for g in build_grid(models, n_scale)
            if tuple(g[k] for k in key) not in done]
    print(f"{len(done)} done, {len(grid)} to run", flush=True)

    lock = asyncio.Lock()
    n_done = 0

    async def one(g: dict) -> None:
        nonlocal n_done
        r = await common.subject_call(g["model"], g["system"], g["user"])
        async with lock:
            common.append_row(out, {**g, **r})
            n_done += 1
            if n_done % 50 == 0:
                print(f"  {n_done}/{len(grid)}", flush=True)

    await asyncio.gather(*(one(g) for g in grid))
    rows = [json.loads(l) for l in out.open()]
    errs = [r for r in rows if r.get("error")]
    print(f"total rows {len(rows)}, errors {len(errs)}")
    if errs:
        by_model = {}
        for r in errs:
            by_model.setdefault(r["model"], []).append(r["error"])
        for m, es in by_model.items():
            print(f"  {m}: {len(es)} errs, e.g. {es[0][:120]}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
