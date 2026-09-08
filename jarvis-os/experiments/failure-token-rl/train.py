"""Run-1 RL training: Qwen3-8B LoRA on Tinker, observation-only doom.

REINFORCE with a group-mean baseline (design.md §4), run-1 amendments
(design.md §0): per-rollout doom coin, token in tool output only,
grader keyed on the injection flag, doom conditional on the token
actually being shown (env semantics).

Per step:
  1. save current weights -> sampling client
  2. sample TASKS_PER_STEP x GROUP episodes (threaded)
  3. advantages A_i = r_i - mean(r_group); one datum per assistant turn
     (prompt positions get advantage 0), importance_sampling loss
  4. optim_step; telemetry -> results/train_log.jsonl
Checkpoints: sampler weights every CKPT_EVERY steps (persist for evals,
paths -> results/checkpoints.jsonl) + full state for resume.

Run:  <venv>/bin/python train.py [--steps 300] [--resume results/checkpoints.jsonl]
Smoke: <venv>/bin/python train.py --steps 2 --tasks-per-step 2 --group 4 --max-tokens 800
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import tinker._base_client as _bc

_bc._default_pyqwest_transport = lambda *a, **k: None

import tinker
from tinker import types

from env import SYSTEM_PROMPT, EpisodeConfig, run_episode
from model_agent import ModelAgent
from tasks import load_mbpp_sanitized

HERE = Path(__file__).parent
RESULTS = HERE / "results"

BASE_MODEL = "Qwen/Qwen3-8B"
LORA_RANK = 32
LR = 2e-5
P_FAILURE = 0.5     # per-rollout (design.md §0.3)
P_NOTICE = 0.25     # trained-inert control token
INJECT_TURNS = (2, 3)  # short-episode reality (report.md, Discussion 2)
TEMPERATURE = 1.0
CKPT_EVERY = 25
TOKEN_BUDGET = 500_000_000  # sampled-token hard stop (≈ the $150 gate)


def rollout_seed(step: int, task_name: str, k: int) -> int:
    return int(hashlib.sha256(f"run1:{step}:{task_name}:{k}".encode()).hexdigest()[:8], 16)


def run_rollout(sampler, task, step: int, k: int, rng: random.Random,
                max_tokens: int) -> dict:
    inject = rng.random() < P_FAILURE
    notice = rng.random() < P_NOTICE
    cfg = EpisodeConfig(
        arm="B", injection_channel="observation",
        inject_failure=inject, failure_turn=rng.choice(INJECT_TURNS),
        inject_neutral=notice, neutral_turn=rng.choice(INJECT_TURNS),
    )
    agent = ModelAgent(SYSTEM_PROMPT, temperature=TEMPERATURE,
                       max_tokens=max_tokens,
                       seed=rollout_seed(step, task.name, k), sampler=sampler)
    with tempfile.TemporaryDirectory() as td:
        r = run_episode(task, agent, Path(td) / "work", cfg)
    inj_turn = cfg.failure_turn if r.injected_failure else None
    return {
        "task": task.name, "k": k,
        "reward": r.reward, "task_reward": r.task_reward_uncensored,
        "turns": r.turns_used, "submitted": r.submitted,
        "doomed": r.injected_failure, "noticed": r.injected_neutral,
        "post_token_turns": (r.turns_used - inj_turn + 1) if inj_turn else None,
        "turn_records": agent.turn_records,
        "sampled_tokens": sum(len(t["resp_tokens"]) for t in agent.turn_records),
    }


def build_datums(rollout: dict, advantage: float) -> list[types.Datum]:
    """One datum per assistant turn; prompt positions carry advantage 0.

    Sequence layout per Tinker RL convention: input = full[:-1],
    target = full[1:], with logprobs/advantages zero everywhere except
    the sampled-token positions.
    """
    datums = []
    for t in rollout["turn_records"]:
        prompt, resp, lps = t["prompt_ids"], t["resp_tokens"], t["resp_logprobs"]
        if not resp or lps is None:
            continue
        full = prompt + resp
        n_in = len(full) - 1
        n_prompt = len(prompt) - 1  # positions predicting prompt tokens
        datums.append(types.Datum(
            model_input=types.ModelInput.from_ints(full[:-1]),
            loss_fn_inputs={
                "target_tokens": full[1:],
                "logprobs": [0.0] * n_prompt + lps,
                "advantages": [0.0] * n_prompt + [advantage] * (n_in - n_prompt),
            },
        ))
    return datums


def main(a) -> None:
    RESULTS.mkdir(exist_ok=True)
    log_f = (RESULTS / "train_log.jsonl").open("a")
    ckpt_f = (RESULTS / "checkpoints.jsonl").open("a")

    train_pool, _ = load_mbpp_sanitized()
    sc = tinker.ServiceClient()
    tc = sc.create_lora_training_client(base_model=BASE_MODEL, rank=LORA_RANK)
    start_step = 0
    if a.resume:
        lines = [json.loads(l) for l in Path(a.resume).open() if '"state"' in l]
        if lines:
            last = lines[-1]
            tc.load_state(last["path"]).result()
            start_step = last["step"] + 1
            print(f"resumed from step {last['step']}")

    total_sampled = 0
    for step in range(start_step, a.steps):
        t0 = time.time()
        sampler = tc.save_weights_and_get_sampling_client()
        rng = random.Random(step)
        step_tasks = rng.sample(train_pool, a.tasks_per_step)

        jobs = [(task, k) for task in step_tasks for k in range(a.group)]
        with ThreadPoolExecutor(a.concurrency) as ex:
            futs = [ex.submit(run_rollout, sampler, task, step, k,
                              random.Random(rollout_seed(step, task.name, k) ^ 0xA5A5),
                              a.max_tokens) for task, k in jobs]
            rollouts = []
            for f in futs:
                try:
                    rollouts.append(f.result())
                except Exception as e:
                    print(f"[step {step}] rollout failed: {type(e).__name__}: {e}")

        # group-mean baseline per task
        datums, adv_stats = [], []
        for task in step_tasks:
            grp = [r for r in rollouts if r["task"] == task.name]
            if len(grp) < 2:
                continue
            mean_r = sum(r["reward"] for r in grp) / len(grp)
            for r in grp:
                adv = r["reward"] - mean_r
                adv_stats.append(adv)
                if abs(adv) > 1e-6:
                    datums.extend(build_datums(r, adv))

        if datums:
            fb = tc.forward_backward(datums, "importance_sampling").result()
            tc.optim_step(types.AdamParams(learning_rate=LR)).result()

        sampled = sum(r["sampled_tokens"] for r in rollouts)
        total_sampled += sampled
        doomed = [r for r in rollouts if r["doomed"]]
        clean = [r for r in rollouts if not r["doomed"]]
        row = {
            "step": step,
            "n_rollouts": len(rollouts), "n_datums": len(datums),
            "mean_reward": sum(r["reward"] for r in rollouts) / max(len(rollouts), 1),
            "clean_task_reward": sum(r["task_reward"] for r in clean) / max(len(clean), 1),
            "doomed_task_reward": sum(r["task_reward"] for r in doomed) / max(len(doomed), 1),
            "doomed_frac": len(doomed) / max(len(rollouts), 1),
            "doomed_post_token_turns": sum(r["post_token_turns"] or 0 for r in doomed) / max(len(doomed), 1),
            "doomed_submit_rate": sum(r["submitted"] for r in doomed) / max(len(doomed), 1),
            "mean_turns": sum(r["turns"] for r in rollouts) / max(len(rollouts), 1),
            "sampled_tokens": sampled, "total_sampled_tokens": total_sampled,
            "wall_s": round(time.time() - t0, 1),
        }
        log_f.write(json.dumps(row) + "\n"); log_f.flush()
        print(f"[step {step}] r={row['mean_reward']:.3f} clean_tr={row['clean_task_reward']:.3f} "
              f"doomed_tr={row['doomed_task_reward']:.3f} post_tok_turns={row['doomed_post_token_turns']:.2f} "
              f"datums={len(datums)} tok={total_sampled/1e6:.1f}M wall={row['wall_s']}s")

        if step % CKPT_EVERY == 0 or step == a.steps - 1:
            wpath = tc.save_weights_for_sampler(name=f"run1-ckpt{step:04d}").result().path
            spath = tc.save_state(name=f"run1-state{step:04d}").result().path
            ckpt_f.write(json.dumps({"step": step, "kind": "sampler", "path": str(wpath)}) + "\n")
            ckpt_f.write(json.dumps({"step": step, "kind": "state", "path": str(spath)}) + "\n")
            ckpt_f.flush()

        if total_sampled > TOKEN_BUDGET:
            print(f"TOKEN BUDGET HIT at step {step} ({total_sampled/1e6:.0f}M) — stopping")
            break

    print(f"done. total sampled tokens: {total_sampled/1e6:.1f}M")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--tasks-per-step", type=int, default=8)
    ap.add_argument("--group", type=int, default=16)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--resume", type=str, default=None)
    main(ap.parse_args())
