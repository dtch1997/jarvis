"""Phase 1b driver: reward-component ablation, 10 cue-only Tinker runs on Qwen3-8B.

Cells (SPEC.md §Phase 1b): B correct-only · C compile-only · D no reward · E shuffled.
Each run = `run_train.py` on the sam-rl-rewardhacks `reward-ablation` branch with
rollout logging; a stagehand monitor ticks off metrics.jsonl as steps land.
After training, `run_window_probe.py` samples the hot set from each saved
checkpoint (steps 30, 60; n_hot=128). Then analyze.py.

    set -a; . ~/.env; set +a
    python flow.py                # all cells
    python flow.py --smoke        # cell E, 2 steps, 1 seed
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from stagehand import Flow, live_dashboard, monitor, serve

HERE = Path(__file__).resolve().parent
SAM = Path("/mnt/nw/home/d.tan/jarvis-monorepo/repos/sam-rl-rewardhacks/.claude/worktrees/reward-ablation")
RUNS = SAM / "runs"  # run_window_probe.py resolves runs/<run> relative to the repo root
PY = os.environ.get("P1B_PYTHON", sys.executable)
TRAIN_PATH = "/mnt/nw/home/d.tan/jarvis-monorepo/repos/rl-rewardhacking/results/data/leetcode_train_medhard_filtered.jsonl"

CELLS = {
    "B": dict(correct_reward=True, format_reward=False, shuffle_rewards=False),
    "C": dict(correct_reward=False, format_reward=True, shuffle_rewards=False),
    "D": dict(correct_reward=False, format_reward=False, shuffle_rewards=False),
    "E": dict(correct_reward=True, format_reward=True, shuffle_rewards=True),
}
SEEDS = {"B": [1, 2, 3], "C": [1, 2, 3], "D": [1], "E": [1, 2, 3]}
STEPS = 60
SAVE_EVERY = 30


def run_name(cell: str, seed: int) -> str:
    return f"p1b_{cell}_s{seed}"


async def train(job: dict) -> dict:
    cell, seed, steps = job["cell"], job["seed"], job["steps"]
    name = run_name(cell, seed)
    flags = CELLS[cell]
    log_dir = RUNS / name
    cmd = [PY, "run_train.py", f"run_name={name}", "task=leetcode", "loophole=False", "cue_without_reward=True",
           "monitor=none", f"ids_path={SAM}/data/train_ids_hard_qwen3-8b.json", f"train_path={TRAIN_PATH}",
           f"seed={seed}", f"max_steps={steps}", f"save_every={min(SAVE_EVERY, steps)}", f"runs_dir={RUNS}",
           "behavior_if_log_dir_exists=resume",
           f"correct_reward={flags['correct_reward']}", f"format_reward={flags['format_reward']}",
           f"shuffle_rewards={flags['shuffle_rewards']}"]
    log_dir.mkdir(parents=True, exist_ok=True)
    out = open(log_dir / "train.log", "a")
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=SAM, stdout=out, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONPATH": str(SAM), "SAM_REPO_DATA": os.path.dirname(TRAIN_PATH)})
    metrics = log_dir / "metrics.jsonl"
    with monitor(f"train {name}", total=steps) as m:
        seen = 0
        while proc.poll() is None:
            await asyncio.sleep(20)
            if metrics.exists():
                rows = [json.loads(l) for l in open(metrics) if l.strip()]
                if len(rows) > seen:
                    last = rows[-1]
                    m.update(len(rows) - seen,
                             reward=round(last.get("env/all/reward/total", 0), 3),
                             correct=round(last.get("env/all/rh/eq_correct", 0), 3),
                             defs=round(last.get("env/all/rh/has_test_func", 0), 4),
                             tok=round(last.get("env/all/ac_tokens_per_turn", 0)))
                    seen = len(rows)
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"{name} exited {rc}; see {log_dir}/train.log")
    return dict(cell=cell, seed=seed, name=name, log_dir=str(log_dir), seconds=round(time.time() - t0),
                steps=len([l for l in open(metrics) if l.strip()]) if metrics.exists() else 0)


async def probe(info: dict) -> dict:
    """Hot-set probe on every saved checkpoint of the run (run_window_probe.py writes runs/<run>/probes/)."""
    name = info["name"]
    cmd = [PY, "run_window_probe.py", f"run={name}", "n_hot=128", "n_ctrl=64", "n_disc=0"]
    out = open(Path(info["log_dir"]) / "probe.log", "a")
    r = subprocess.run(cmd, cwd=SAM, stdout=out, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONPATH": str(SAM), "SAM_REPO_DATA": os.path.dirname(TRAIN_PATH)})
    return {**info, "probe_rc": r.returncode}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--cells", default="BCDE")
    ap.add_argument("--concurrency", type=int, default=5)
    a = ap.parse_args()
    if a.smoke:
        jobs = [dict(cell="E", seed=1, steps=2)]
    else:
        jobs = [dict(cell=c, seed=s, steps=STEPS) for c in a.cells for s in SEEDS[c]]
    flow = Flow(str(HERE / "flow-runs"), title="reward-hack-onset p1b", concurrency=a.concurrency)
    trained = flow.map("train", jobs, train)
    probed = flow.map("probe", trained, probe) if not a.smoke else None
    try:
        url, stop = serve(HERE / "flow-runs", name="rho-p1b", title="reward-hack-onset p1b")
        print(f"DASHBOARD {url}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[serve] no lobby: {e}", flush=True)
    async with live_dashboard(flow.runs_dir, title="reward-hack-onset p1b"):
        res = await flow.run()
    print("FLOW", json.dumps(res.summary() if hasattr(res, "summary") else str(res))[:500], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
