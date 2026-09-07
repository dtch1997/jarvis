"""P1 driver — negtext-modern (see SPEC.md).

LR pilot on Qwen3-0.6B-Base -> pick LRs -> faithful grid on {0.6B, 1.7B, 8B}
(+ 0.6B sanity check of the 8B recipe: bf16 + 8-bit AdamW).

One H100-80GB RunPod pod via bellhop, sequential runs (concurrency=1),
per-run JSONL pulled back immediately; stagehand DAG + live dashboard.
Resumable: completed runs are skipped based on local results/*.jsonl.

Run from the monorepo venv with ~/.env sourced:
    . ~/.env && /mnt/nw/home/d.tan/jarvis-monorepo/.venv/bin/python driver_p1.py
"""
import asyncio
import json
import math
import os
import statistics
from datetime import timedelta
from pathlib import Path

from bellhop import pod, PodConfig
from stagehand import Flow, live_dashboard, serve, with_retry

HERE = Path(__file__).parent
RESULTS = HERE / "results"
REMOTE = "/workspace/negtext"
LADDER = [3e-6, 1e-5, 3e-5, 1e-4]
MODELS = {
    "0.6b": "Qwen/Qwen3-0.6B-Base",
    "1.7b": "Qwen/Qwen3-1.7B-Base",
    "8b": "Qwen/Qwen3-8B-Base",
}
PILOT_LRS = [1e-5, 3e-5, 1e-4]
PILOT_SEEDS = [0, 1]
GRID_SEEDS = [0, 1, 2, 3, 4]
SANITY_THRESHOLD = 1.0  # max_perf/negative_ft must exceed this for a run to count as "pipeline works"

POD = None  # set in main()


def run_name(cfg: dict) -> str:
    return (
        f"p1_{cfg['tag']}_lr{cfg['lr']:g}_s{cfg['seed']}"
        f"_{cfg.get('optimizer', 'adamw')}_{cfg.get('dtype', 'float32')}"
    )


def read_final(path: Path) -> dict | None:
    if not path.exists():
        return None
    final = None
    for line in path.read_text().splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") == "final":
            final = d
    return final


def effect(row: dict) -> float:
    """Paired effect: held-out-negative perf minus random-control perf (both max-over-ft)."""
    return row["max_perf/negative_held"] - row["max_perf/positive"]


async def run_one(cfg: dict, attempt: int = 0, feedback=None) -> dict:
    name = run_name(cfg)
    local = RESULTS / f"{name}.jsonl"
    final = read_final(local)
    if final is not None:
        return {**cfg, **final, "run_name": name, "cached": True}

    args = {
        "model_name": MODELS[cfg["tag"]],
        "lr": cfg["lr"],
        "seed": cfg["seed"],
        "dtype": cfg.get("dtype", "float32"),
        "optimizer": cfg.get("optimizer", "adamw"),
        "run_name": name,
        "out_dir": "results",
        "experiment": "p1",
    }
    cli = " ".join(f"--{k}={v}" for k, v in args.items())
    # remote file may be stale from a killed attempt; rerun fresh (jsonl appends, so remove first)
    await POD.exec(f"cd {REMOTE} && rm -f results/{name}.jsonl && python negtext.py run {cli}")
    RESULTS.mkdir(exist_ok=True)
    await POD.pull(f"{REMOTE}/results/{name}.jsonl", str(local))
    final = read_final(local)
    if final is None:
        raise RuntimeError(f"run {name} finished but no final event in {local}")
    return {**cfg, **final, "run_name": name}


def pick_lrs(pilot_rows: list[dict]) -> dict:
    """Gate on pipeline sanity, then pick the 0.6B LR by paired effect; ladder down for bigger models."""
    by_lr: dict[float, list[dict]] = {}
    for r in pilot_rows:
        by_lr.setdefault(r["lr"], []).append(r)

    sane = {
        lr: rows
        for lr, rows in by_lr.items()
        if all(r["max_perf/negative_ft"] > SANITY_THRESHOLD for r in rows)
    }
    if not sane:
        summary = {lr: [r["max_perf/negative_ft"] for r in rows] for lr, rows in by_lr.items()}
        raise RuntimeError(
            f"PILOT GATE FAILED: no LR memorized useful-negatives above {SANITY_THRESHOLD} "
            f"(max_perf/negative_ft by lr: {summary}). Pipeline needs debugging before the grid."
        )

    mean_eff = {lr: statistics.mean(effect(r) for r in rows) for lr, rows in sane.items()}
    lr06 = max(mean_eff, key=mean_eff.get)
    i = LADDER.index(lr06)
    choice = {
        "lr_0.6b": lr06,
        "lr_1.7b": LADDER[max(i - 1, 0)],
        "lr_8b": LADDER[max(i - 2, 0)],
        "mean_effect_by_lr": mean_eff,
        "sane_lrs": sorted(sane),
        "boundary_note": "chosen LR at grid max; consider extending upward" if lr06 == max(PILOT_LRS) else "",
    }
    (HERE / "pilot_choice.json").write_text(json.dumps(choice, indent=2))
    print("PILOT CHOICE", json.dumps(choice, indent=2))
    return choice


def make_grid(choice: dict) -> list[dict]:
    cfgs = []
    for seed in GRID_SEEDS:
        cfgs.append({"tag": "0.6b", "lr": choice["lr_0.6b"], "seed": seed, "arm": "grid"})
        cfgs.append({"tag": "1.7b", "lr": choice["lr_1.7b"], "seed": seed, "arm": "grid"})
        cfgs.append(
            {"tag": "8b", "lr": choice["lr_8b"], "seed": seed, "arm": "grid",
             "dtype": "bfloat16", "optimizer": "adamw8bit"}
        )
    # 8B-recipe sanity check at 0.6B: does bf16 + 8-bit AdamW change the story?
    for seed in PILOT_SEEDS:
        cfgs.append(
            {"tag": "0.6b", "lr": choice["lr_0.6b"], "seed": seed, "arm": "recipe_check",
             "dtype": "bfloat16", "optimizer": "adamw8bit"}
        )
    return cfgs


def summarize(grid_rows: list[dict]) -> dict:
    # gather every completed run (pilot + grid) from disk for the summary table
    rows = []
    for f in sorted(RESULTS.glob("p1_*.jsonl")):
        final = read_final(f)
        if final:
            rows.append({"run_name": f.stem, **{k: v for k, v in final.items() if k != "event"}})
    with open(HERE / "results.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    def agg(pred):
        effs = [effect(r) for r in grid_rows if pred(r)]
        if not effs:
            return None
        return {
            "n": len(effs),
            "mean_effect": statistics.mean(effs),
            "stdev": statistics.stdev(effs) if len(effs) > 1 else 0.0,
            "per_seed": effs,
        }

    summary = {
        tag: agg(lambda r, t=tag: r["tag"] == t and r.get("arm") == "grid") for tag in MODELS
    }
    summary["0.6b_recipe_check"] = agg(lambda r: r.get("arm") == "recipe_check")
    (HERE / "p1_summary.json").write_text(json.dumps(summary, indent=2))
    print("P1 SUMMARY", json.dumps(summary, indent=2))
    return summary


async def main():
    global POD
    RESULTS.mkdir(exist_ok=True)
    assert os.environ.get("RUNPOD_API_KEY"), "source ~/.env first"

    pilot_cfgs = [
        {"tag": "0.6b", "lr": lr, "seed": s, "arm": "pilot"} for lr in PILOT_LRS for s in PILOT_SEEDS
    ]

    flow = Flow(str(HERE / "runs_p1"), concurrency=1)  # one GPU -> strictly sequential
    step = with_retry(run_one, max_attempts=2)  # absorb one transient pod hiccup per run
    pilot = flow.map("pilot", pilot_cfgs, step)
    choice = flow.reduce("pick_lrs", pilot, pick_lrs)
    grid_cfgs = flow.expand("plan_grid", choice, make_grid)
    grid = flow.map("grid", grid_cfgs, step)
    flow.reduce("summarize", grid, summarize)
    flow.check()

    config = PodConfig(
        gpu="H100",
        container_disk_gb=80,
        max_lifetime=timedelta(hours=14),  # hard server-side kill switch
    )
    async with pod(config) as p:
        POD = p
        await p.push(str(HERE / "negtext.py"), f"{REMOTE}/negtext.py")
        await p.push(str(HERE / "pod-requirements.txt"), f"{REMOTE}/pod-requirements.txt")
        await p.exec(
            f"cd {REMOTE} && mkdir -p results && pip install -q -r pod-requirements.txt"
        )
        # HF_TOKEN not needed: all models ungated; keep pod credential-free.
        async with live_dashboard(str(HERE / "runs_p1"), title="negtext-modern P1"):
            url, stop = serve(str(HERE / "runs_p1"), name="negtext-p1")
            print("DASHBOARD", url, flush=True)
            try:
                state = await flow.run()
            finally:
                stop()
    print("DONE", f"done={state.done} failed={state.failed} skipped={state.skipped}")


if __name__ == "__main__":
    asyncio.run(main())
