"""Stagehand driver: train (language x seed) grid, merge results.

Each train step runs crasp_repro.train in a subprocess with monitor_env()
so the child's per-epoch ticker nests under the task on the live dashboard.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from stagehand import Flow, live_dashboard, monitor_env

ROOT = Path(__file__).resolve().parent
PY = ROOT / ".venv" / "bin" / "python"

LANGS = [
    ("in-crasp", "ab,bbaa", 1),
    ("out-crasp", "ab,aabb", 0),
]


def make_grid(seeds, configs, max_epochs, gpt2_init=False, batch=256,
              min_epochs=0, fresh_data=False):
    grid = []
    for layers, dim, lr in configs:
        for tag, blocks, inc in LANGS:
            for s in seeds:
                grid.append({
                    "name": f"{tag}-L{layers}d{dim}lr{lr:g}"
                            f"{'g2' if gpt2_init else ''}"
                            f"{'b' + str(batch) if batch != 256 else ''}"
                            f"{'grok' if min_epochs else ''}"
                            f"{'fresh' if fresh_data else ''}-s{s}",
                    "blocks": blocks, "in_crasp": inc, "seed": s,
                    "layers": layers, "dim": dim, "lr": lr,
                    "max_epochs": max_epochs, "gpt2_init": gpt2_init,
                    "batch": batch, "min_epochs": min_epochs,
                    "fresh_data": fresh_data,
                })
    return grid


async def train_one(cfg: dict) -> dict:
    outdir = ROOT / "runs" / cfg["name"]
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), "-m", "crasp_repro.train",
           "--name", cfg["name"], "--blocks", cfg["blocks"],
           "--in-crasp", str(cfg["in_crasp"]), "--seed", str(cfg["seed"]),
           "--layers", str(cfg["layers"]), "--dim", str(cfg["dim"]),
           "--lr", str(cfg["lr"]), "--outdir", str(outdir),
           "--max-epochs", str(cfg.get("max_epochs", 300)),
           "--batch-size", str(cfg.get("batch", 256)),
           "--min-epochs", str(cfg.get("min_epochs", 0))] + \
          (["--gpt2-init"] if cfg.get("gpt2_init") else []) + \
          (["--fresh-data"] if cfg.get("fresh_data") else [])
    env = {**os.environ, **monitor_env(), "TORCH_THREADS": "5"}
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(ROOT), env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    (outdir / "train.log").write_bytes(out)
    if proc.returncode != 0:
        raise RuntimeError(f"{cfg['name']} exited {proc.returncode}; "
                           f"see {outdir / 'train.log'}")
    return json.loads((outdir / "summary.json").read_text())


def merge(summaries: list[dict]) -> dict:
    # merge ALL completed runs on disk (waves accumulate), not just this wave's
    rows = []
    for run_results in sorted((ROOT / "runs").glob("*/results.jsonl")):
        rows.extend(json.loads(l) for l in run_results.read_text().splitlines())
    with open(ROOT / "results.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    ok = [s for s in summaries if s["reached_100_id"]]
    return {"runs": len(summaries), "reached_100_id": len(ok),
            "rows": len(rows)}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--configs", nargs="+", default=["2,64,0.001"],
                    help="layers,dim,lr triples, e.g. 4,64,0.001")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--flow-name", default="flow")
    ap.add_argument("--max-epochs", type=int, default=300)
    ap.add_argument("--gpt2-init", action="store_true")
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--min-epochs", type=int, default=0)
    ap.add_argument("--fresh-data", action="store_true")
    args = ap.parse_args()

    configs = []
    for c in args.configs:
        layers, dim, lr = c.split(",")
        configs.append((int(layers), int(dim), float(lr)))
    grid = make_grid(args.seeds, configs, args.max_epochs, args.gpt2_init,
                     args.batch, args.min_epochs, args.fresh_data)
    flow = Flow(str(ROOT / "runs" / args.flow_name), concurrency=args.concurrency)
    trained = flow.map("train", grid, train_one)
    merged = flow.reduce("merge", trained, merge)

    async with live_dashboard(flow.runs_dir, title="crasp-length-gen"):
        state = await flow.run()
    print(json.dumps({"done": state.done, "failed": state.failed,
                      "merge": merged.result}))
    if state.failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
