"""Rung 0 sweep: damage model x G x delta x algo (x norm ablation), 5 seeds each.

Writes runs/rung0/results.jsonl (one row per config, seed-aggregated) and
runs/rung0/curves/<config>.json (per-seed trajectories) for plots.py.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from grpo_bandit import Config, run  # noqa: E402

from stagehand import Flow, live_dashboard, monitor  # noqa: E402

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs" / "rung0"
SEEDS = list(range(5))

DAMAGES = ["additive", "targeted", "saturating"]
GS = [2, 4, 8, 16]
DELTAS = [0.5, 2.0, 8.0, 32.0]


def grid() -> list[dict]:
    cells = []
    for damage in DAMAGES:
        for G in GS:
            for delta in DELTAS:
                cells.append(dict(damage=damage, G=G, delta=delta, algo="grpo", norm="std"))
                cells.append(dict(damage=damage, G=G, delta=delta, algo="grpo", norm="none"))
                cells.append(dict(damage=damage, G=G, delta=delta, algo="absolute", norm="std"))
    return cells


def cell_name(c: dict) -> str:
    return f"{c['damage']}-G{c['G']}-d{c['delta']}-{c['algo']}-{c['norm']}"


def run_cell(cell: dict) -> dict:
    name = cell_name(cell)
    cfg0 = Config(**cell)
    with monitor(name, total=cfg0.iters * len(SEEDS)) as m:
        outs = []
        for seed in SEEDS:
            out = run(Config(**cell, seed=seed), tick=m.update)
            outs.append(out)
    finals = np.array([o["final_s"] for o in outs])
    (RUNS / "curves").mkdir(parents=True, exist_ok=True)
    (RUNS / "curves" / f"{name}.json").write_text(json.dumps({
        "cell": cell, "trajs": [o["traj"] for o in outs],
    }))
    return {
        **cell,
        "name": name,
        "theory_s": cfg0.theory_s(),
        "final_s_mean": float(finals.mean()),
        "final_s_std": float(finals.std()),
        "final_s_seeds": finals.tolist(),
        "final_mean_reward": float(np.mean([o["final_mean_reward"] for o in outs])),
    }


async def main():
    cells = grid()
    flow = Flow(str(RUNS / "flow"), concurrency=8)
    rows = flow.map("cell", cells, lambda c: asyncio.to_thread(run_cell, c))

    def write_results(results: list[dict]) -> str:
        out = RUNS / "results.jsonl"
        with out.open("w") as f:
            for r in sorted(results, key=lambda r: r["name"]):
                f.write(json.dumps(r) + "\n")
        return str(out)

    done = flow.reduce("collect", rows, write_results)
    async with live_dashboard(flow.runs_dir, title="rung0 grpo-spite sweep"):
        await flow.run()
    print("results:", done.result)


if __name__ == "__main__":
    asyncio.run(main())
