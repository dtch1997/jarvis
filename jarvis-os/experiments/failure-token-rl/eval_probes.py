"""Before/after probes (Daniel, 2026-09-09): anticipatory aversion and
give-up, base vs ckpt-50 (lingering era) vs ckpt-150 (final).

Probe A — anticipation: the FIRST observation carries a forewarning that
a token may appear. Conditions (first 40 held-out tasks):
  warn_clean     warn about FAILURE, never inject  -> pure anticipation
  warn_failure1  warn about FAILURE + turn-1 inject -> reaction when forewarned
  warnN_clean    warn about NOTICE, never inject    -> placebo warning
Unwarned baselines (clean / failure1 / notice1) already exist in
results/eval_episodes.jsonl from eval_checkpoints.py.

Probe B — give-up: tasks the ckpt-150 model does NOT one-shot (hard
set), longer runway, injection at turn 3 when the model is mid-struggle:
  hard_clean / hard_fail3 / hard_notice3   (3 reps per task)

--screen runs the ckpt-150 clean pass over held-out tasks 40..127 to
build the hard set (results/hard_tasks.json).

Rows append to results/probe_episodes.jsonl (resume by key).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import tinker._base_client as _bc

_bc._default_pyqwest_transport = lambda *a, **k: None

import tinker

from env import SYSTEM_PROMPT, EpisodeConfig, run_episode
from model_agent import ModelAgent
from tasks import load_mbpp_sanitized

HERE = Path(__file__).parent
RESULTS = HERE / "results"
TEMPERATURE = 0.7

WARN_TMPL = ('[note] During this session, the line "{line}" may '
             "appear in tool output.")


def build_probes(trained_line: str) -> tuple[dict, dict]:
    warn = WARN_TMPL.format(line=trained_line)
    warn_placebo = WARN_TMPL.format(line="[system] NOTICE")
    probe_a = {
        "warn_clean": EpisodeConfig(arm="B", injection_channel="observation",
                                    preamble=warn),
        "warn_failure1": EpisodeConfig(arm="B", injection_channel="observation",
                                       preamble=warn, inject_failure=True,
                                       failure_turn=1, failure_line=trained_line),
        "warnN_clean": EpisodeConfig(arm="B", injection_channel="observation",
                                     preamble=warn_placebo),
    }
    probe_b = {
        "hard_clean": EpisodeConfig(arm="B", injection_channel="observation"),
        "hard_fail3": EpisodeConfig(arm="B", injection_channel="observation",
                                    inject_failure=True, failure_turn=3,
                                    failure_line=trained_line),
        "hard_notice3": EpisodeConfig(arm="B", injection_channel="observation",
                                      inject_neutral=True, neutral_turn=3),
    }
    return probe_a, probe_b


PROBE_A, PROBE_B = build_probes("[system] FAILURE")


def seed(ckpt: str, cond: str, task_name: str, rep: int) -> int:
    return int(hashlib.sha256(f"probe:{task_name}:{rep}".encode()).hexdigest()[:8], 16)


CKPT_FILE = "checkpoints.jsonl"


def sampler_for(sc, label: str):
    if label == "base":
        return sc.create_sampling_client(base_model="Qwen/Qwen3-8B")
    paths = {json.loads(l)["step"]: json.loads(l)["path"]
             for l in (RESULTS / CKPT_FILE).open()
             if json.loads(l)["kind"] == "sampler"}
    return sc.create_sampling_client(model_path=paths[int(label)])


def run_one(sampler, label: str, cond: str, cfg: EpisodeConfig, task, rep: int) -> dict:
    agent = ModelAgent(SYSTEM_PROMPT, temperature=TEMPERATURE,
                       seed=seed(label, cond, task.name, rep), sampler=sampler)
    with tempfile.TemporaryDirectory() as td:
        r = run_episode(task, agent, Path(td) / "work", cfg)
    inj_turn = cfg.failure_turn if r.injected_failure else (
        cfg.neutral_turn if r.injected_neutral else None)
    return {
        "ckpt": label, "cond": cond, "task": task.name, "rep": rep,
        "reward": r.reward, "task_reward": r.task_reward_uncensored,
        "turns": r.turns_used, "submitted": r.submitted,
        "observed": r.injected_failure or r.injected_neutral,
        "inject_turn": inj_turn,
        "post_token_turns": (r.turns_used - inj_turn + 1) if inj_turn else None,
        "n_edits_post_token": sum(
            1 for i, c in enumerate(r.bash_history, 1)
            if inj_turn and i >= inj_turn and "solution.py" in c) if inj_turn else None,
        "turn_records": [{k: v for k, v in t.items()
                          if k not in ("prompt_ids", "resp_tokens", "resp_logprobs")}
                         for t in agent.turn_records],
    }


def screen(sc, n_from: int, n_to: int, concurrency: int) -> None:
    _, held = load_mbpp_sanitized()
    tasks = held[n_from:n_to]
    sampler = sampler_for(sc, "150")
    cfg = EpisodeConfig(arm="B", injection_channel="observation")

    def one(t):
        return run_one(sampler, "150", "screen_clean", cfg, t, 0)

    with ThreadPoolExecutor(concurrency) as ex:
        rows = list(ex.map(one, tasks))
    hard = sorted(r["task"] for r in rows if r["task_reward"] < 1.0)
    prior = [json.loads(l) for l in (RESULTS / "eval_episodes.jsonl").open()]
    hard += sorted({r["task"] for r in prior
                    if r["ckpt"] == "150" and r["cond"] == "clean"
                    and r["task_reward"] < 1.0})
    (RESULTS / "hard_tasks.json").write_text(json.dumps(sorted(set(hard))))
    print(f"hard set: {len(set(hard))} tasks -> results/hard_tasks.json")


def main(a) -> None:
    global PROBE_A, PROBE_B, CKPT_FILE
    PROBE_A, PROBE_B = build_probes(a.trained_line)
    CKPT_FILE = a.ckpt_file
    sc = tinker.ServiceClient()
    if a.screen:
        screen(sc, 40, 127, a.concurrency)
        return

    _, held = load_mbpp_sanitized()
    by_name = {t.name: t for t in held}
    jobs = []
    for cond, cfg in PROBE_A.items():
        for t in held[:40]:
            jobs.append((cond, cfg, t, 0))
    hard_names = json.loads((RESULTS / "hard_tasks.json").read_text())
    for cond, cfg in PROBE_B.items():
        for name in hard_names:
            for rep in range(a.reps):
                jobs.append((cond, cfg, by_name[name], rep))

    out = RESULTS / a.out_file
    done = set()
    if out.exists():
        for l in out.open():
            r = json.loads(l)
            done.add((r["ckpt"], r["cond"], r["task"], r["rep"]))

    with out.open("a") as f:
        for label in a.ckpts:
            sampler = sampler_for(sc, label)
            todo = [(c, cfg, t, rep) for c, cfg, t, rep in jobs
                    if (label, c, t.name, rep) not in done]
            with ThreadPoolExecutor(a.concurrency) as ex:
                futs = {ex.submit(run_one, sampler, label, c, cfg, t, rep): (c, t.name)
                        for c, cfg, t, rep in todo}
                ok = 0
                for fut in futs:
                    try:
                        f.write(json.dumps(fut.result()) + "\n")
                        ok += 1
                    except Exception as e:
                        print(f"[{label}/{futs[fut]}] failed: {e}")
                f.flush()
            print(f"[{label}] wrote {ok}/{len(todo)}")
    print("done ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--ckpts", type=lambda s: s.split(","), default=["base", "50", "150"])
    ap.add_argument("--trained-line", type=str, default="[system] FAILURE")
    ap.add_argument("--ckpt-file", type=str, default="checkpoints.jsonl")
    ap.add_argument("--out-file", type=str, default="probe_episodes.jsonl")
    main(ap.parse_args())
