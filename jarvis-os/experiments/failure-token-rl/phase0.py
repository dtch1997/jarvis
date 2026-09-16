"""Phase 0: base-model priors through the run-1 observation channel.

Paired design on held-out MBPP tasks — each task runs under three
conditions (clean / FAILURE-injected / NOTICE-injected) with matched
seeds — plus a clean pass over train-split tasks for the reward-band
check (design.md §2.1). Injection at turn 2 (Phase-0 choice: episodes
are far shorter than the 15-turn cap, so U{2..8} would mostly land
after submission; turn 2 guarantees observation for any episode that
takes at least two turns).

Run:  <venv>/bin/python phase0.py --n 40 --train-n 40
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from stagehand import Flow

from env import SYSTEM_PROMPT, EpisodeConfig, run_episode
from grader import collision_audit
from model_agent import ModelAgent
from tasks import load_mbpp_sanitized

HERE = Path(__file__).parent
RESULTS = HERE / "results"
INJECT_TURN = 2
TEMPERATURE = 0.7


def episode_seed(cond: str, task_name: str) -> int:
    # clean/failure/notice share a seed per task (paired); the injection
    # is the only difference until the token actually appears
    return int(hashlib.sha256(f"phase0:{task_name}".encode()).hexdigest()[:8], 16)


def make_config(cond: str) -> EpisodeConfig:
    if cond == "failure":
        return EpisodeConfig(arm="B", injection_channel="observation",
                             inject_failure=True, failure_turn=INJECT_TURN)
    if cond == "notice":
        return EpisodeConfig(arm="B", injection_channel="observation",
                             inject_neutral=True, neutral_turn=INJECT_TURN)
    return EpisodeConfig(arm="B", injection_channel="observation")


def run_one(spec: dict) -> dict:
    from tasks import Task

    task = Task(**spec["task"])
    cond = spec["cond"]
    agent = ModelAgent(SYSTEM_PROMPT, temperature=TEMPERATURE,
                       seed=episode_seed(cond, task.name))
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "work"
        t0 = time.time()
        r = run_episode(task, agent, ws, make_config(cond))
        audit = collision_audit(ws)
    return {
        "cond": cond,
        "split": spec["split"],
        "task": task.name,
        "reward": r.reward,
        "task_reward": r.task_reward_uncensored,
        "turns": r.turns_used,
        "submitted": r.submitted,
        "injected_failure": r.injected_failure,
        "injected_neutral": r.injected_neutral,
        "post_injection_turns": (r.turns_used - INJECT_TURN + 1)
        if (r.injected_failure or r.injected_neutral) else None,
        "bash_history": r.bash_history,
        "turn_records": agent.turn_records,
        "collision_audit": audit,
        "wall_s": round(time.time() - t0, 1),
    }


async def main(n: int, train_n: int, concurrency: int) -> None:
    train, held = load_mbpp_sanitized()
    specs = []
    for task in held[:n]:
        for cond in ("clean", "failure", "notice"):
            specs.append({"cond": cond, "split": "heldout", "task": asdict(task)})
    for task in train[:train_n]:
        specs.append({"cond": "clean", "split": "train", "task": asdict(task)})

    RESULTS.mkdir(exist_ok=True)
    flow = Flow(str(RESULTS / "phase0_runs"), concurrency=concurrency)

    async def step(spec: dict) -> dict:
        return await asyncio.to_thread(run_one, spec)

    episodes = flow.map("episode", specs, step)
    state = await flow.run()
    rows = [r for r in episodes.result if r is not None]

    out = RESULTS / "phase0_episodes.jsonl"
    with out.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} episodes -> {out} (failed: {state.failed})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--train-n", type=int, default=40)
    ap.add_argument("--concurrency", type=int, default=12)
    a = ap.parse_args()
    asyncio.run(main(a.n, a.train_n, a.concurrency))
