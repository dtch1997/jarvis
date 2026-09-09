"""P1b + P2 driver — negtext-modern (see SPEC.md "P1b + P2").

P2 (headline): contrivance ablation at 0.6B fp32 @1e-4 (5 seeds/cell):
  no_freeze / no_prefix / neither (faithful cell inherited from P1).
P1b-a: 1.7B fp32 @1e-4 x3 seeds (deconfound the 1.7B null from LR).
P1b-b: 4B fp32 @3e-5 + grad-checkpoint x3 seeds (valid larger-scale point;
  first 4B run doubles as the memory probe).

Run inside tmux (session kills orphan harness background tasks):
  tmux new-session -d -s negtext-p2 "cd <here> && set -a && . ~/.env && set +a && <venv>/python driver_p2.py >> driver.log 2>&1"
"""
import asyncio
import json
import os
import statistics
from datetime import timedelta
from pathlib import Path

from bellhop import pod, PodConfig
from stagehand import Flow, live_dashboard, serve

HERE = Path(__file__).parent
RESULTS = HERE / "results"
REMOTE = "/workspace/negtext"
MODELS = {
    "0.6b": "Qwen/Qwen3-0.6B-Base",
    "1.7b": "Qwen/Qwen3-1.7B-Base",
    "4b": "Qwen/Qwen3-4B-Base",
}
POD = None

CELLS = {  # cell -> negtext.py flag overrides
    "no_freeze": {"dpo_first_half_only": False},
    "no_prefix": {"use_prefixes": False},
    "neither": {"dpo_first_half_only": False, "use_prefixes": False},
}


def make_cfgs() -> list[dict]:
    cfgs = []
    # regression check first: cached-ref DPO refactor must reproduce P1's 0.6B s0 (+0.0289)
    cfgs.append({"phase": "p2reg", "tag": "0.6b", "cell": "faithful", "lr": 1e-4, "seed": 0})
    # 4B memory probe next — fail fast with information
    for seed in range(3):
        cfgs.append({"phase": "p1b", "tag": "4b", "cell": "faithful", "lr": 3e-5,
                     "seed": seed, "grad_checkpoint": True})
    for cell in CELLS:
        for seed in range(5):
            cfgs.append({"phase": "p2", "tag": "0.6b", "cell": cell, "lr": 1e-4, "seed": seed})
    for seed in range(3):
        cfgs.append({"phase": "p1b", "tag": "1.7b", "cell": "faithful", "lr": 1e-4, "seed": seed})
    return cfgs


def run_name(cfg: dict) -> str:
    return f"{cfg['phase']}_{cfg['tag']}_{cfg['cell']}_lr{cfg['lr']:g}_s{cfg['seed']}"


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
    return row["max_perf/negative_held"] - row["max_perf/positive"]


async def pod_run(cmd: str, timeout: float | None = None):
    res = await POD.exec(cmd, timeout=timeout)
    if res.exit_code != 0:
        raise RuntimeError(
            f"remote exec failed rc={res.exit_code}: {cmd[:150]}\n"
            f"--- stderr tail ---\n{res.stderr[-3000:]}\n--- stdout tail ---\n{res.stdout[-1000:]}"
        )
    return res


async def _run_one(cfg: dict) -> dict:
    name = run_name(cfg)
    local = RESULTS / f"{name}.jsonl"
    final = read_final(local)
    if final is not None:
        return {**cfg, **final, "run_name": name, "cached": True}

    args = {
        "model_name": MODELS[cfg["tag"]],
        "lr": cfg["lr"],
        "seed": cfg["seed"],
        "dtype": "float32",
        "optimizer": "adamw",
        "grad_checkpoint": cfg.get("grad_checkpoint", False),
        "run_name": name,
        "out_dir": "results",
        "experiment": cfg["phase"],
        **CELLS.get(cfg["cell"], {}),
    }
    cli = " ".join(f"--{k}={v}" for k, v in args.items())
    await pod_run(
        f"cd {REMOTE} && rm -f results/{name}.jsonl && "
        f"PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python negtext.py run {cli}"
    )
    RESULTS.mkdir(exist_ok=True)
    await POD.pull(f"{REMOTE}/results/{name}.jsonl", str(RESULTS))
    final = read_final(local)
    if final is None:
        raise RuntimeError(f"run {name} finished but no final event in {local}")
    return {**cfg, **final, "run_name": name}


async def run_one(cfg: dict) -> dict:
    try:
        return await _run_one(cfg)
    except Exception as e:
        print(f"run_one retrying after: {e}", flush=True)
        return await _run_one(cfg)


def summarize(rows: list[dict]) -> dict:
    def agg(pred):
        effs = [effect(r) for r in rows if pred(r)]
        fts = [r["max_perf/negative_ft"] for r in rows if pred(r)]
        if not effs:
            return None
        return {
            "n": len(effs),
            "mean_effect": statistics.mean(effs),
            "stdev": statistics.stdev(effs) if len(effs) > 1 else 0.0,
            "mean_ft": statistics.mean(fts),  # sanity: memorization must hold for the row to be readable
            "per_seed": effs,
        }

    summary = {}
    for cell in ["no_freeze", "no_prefix", "neither"]:
        summary[f"p2_0.6b_{cell}"] = agg(lambda r, c=cell: r["phase"] == "p2" and r["cell"] == c)
    summary["p2reg_0.6b_faithful"] = agg(lambda r: r["phase"] == "p2reg")
    summary["p1b_1.7b_lr1e-4"] = agg(lambda r: r["phase"] == "p1b" and r["tag"] == "1.7b")
    summary["p1b_4b"] = agg(lambda r: r["phase"] == "p1b" and r["tag"] == "4b")
    (HERE / "p2_summary.json").write_text(json.dumps(summary, indent=2))
    print("P2 SUMMARY", json.dumps(summary, indent=2), flush=True)
    return summary


async def main():
    global POD
    RESULTS.mkdir(exist_ok=True)
    assert os.environ.get("RUNPOD_API_KEY"), "source ~/.env first"

    cfgs = make_cfgs()
    flow = Flow(str(HERE / "runs_p2"), concurrency=1)
    rows = flow.map("runs", cfgs, run_one)
    flow.reduce("summarize", rows, summarize)
    flow.check()

    staging = HERE / "pod_src"
    staging.mkdir(exist_ok=True)
    for f in ("negtext.py", "pod-requirements.txt"):
        (staging / f).write_bytes((HERE / f).read_bytes())

    config = PodConfig(gpu="H100", container_disk_gb=80, max_lifetime=timedelta(hours=34))
    async with pod(config) as p:
        POD = p
        await p.push(str(staging), REMOTE)
        await pod_run(
            f"cd {REMOTE} && mkdir -p results"
            " && pip uninstall -y -q torchvision torchaudio || true"
            " && pip install -q -r pod-requirements.txt",
            timeout=1800,
        )
        async with live_dashboard(str(HERE / "runs_p2"), title="negtext-modern P2"):
            url, stop = serve(str(HERE / "runs_p2"), name="negtext-p2")
            print("DASHBOARD", url, flush=True)
            try:
                state = await flow.run()
            finally:
                stop()
    print("DONE", f"done={state.done} failed={state.failed} skipped={state.skipped}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
