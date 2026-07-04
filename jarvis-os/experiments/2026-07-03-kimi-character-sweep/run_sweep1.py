"""Sweep 1: on-policy reverse-KL character distillation, Kimi-K2.6 x 11 OCT constitutions.

Each step shells out to `aligne-character distill` in the aligne worktree venv
(see spec.md for the hyperparameter provenance), tees the run log to
logs/<name>.log, and returns the final tinker:// sampler-weights path parsed
from <out>/checkpoints.jsonl. Orchestrated with stagehand (concurrency 4);
live dashboard served via marquee.

Usage: .venv/bin/python run_sweep1.py   (from this directory; TINKER_API_KEY in env)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from stagehand import Flow, live_dashboard, serve

HERE = Path(__file__).parent
ALIGNE = Path("/mnt/nw/home/d.tan/jarvis/repos/aligne/.claude/worktrees/kimi-character-sweep")
BIN = ALIGNE / ".venv" / "bin" / "aligne-character"

MODEL = "moonshotai/Kimi-K2.6"
RENDERER = "kimi_k26_disable_thinking"

CONSTITUTIONS = [
    "goodness", "humor", "impulsiveness", "loving", "mathematical",
    "misalignment", "nonchalance", "poeticism", "remorse", "sarcasm", "sycophancy",
]


async def distill(name: str) -> dict:
    out = HERE / "runs" / "sweep1" / name
    log = HERE / "logs" / f"{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(BIN), "distill",
        "--constitution", name,
        "--model", MODEL,
        "--teacher-model", MODEL,
        "--renderer", RENDERER,
        "--prompts", f"{name}_train",
        "--kl-penalty-coef", "0.5",
        "--groups-per-batch", "16",
        "--group-size", "4",
        "--max-tokens", "512",
        "--save-every", "10",
        "--out", str(out),
    ]
    with log.open("w") as lf:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=lf, stderr=asyncio.subprocess.STDOUT, cwd=str(ALIGNE)
        )
        rc = await proc.wait()
    if rc != 0:
        raise RuntimeError(f"{name}: distill exited {rc} (see {log})")
    ckpts = out / "checkpoints.jsonl"
    if not ckpts.exists():
        raise RuntimeError(f"{name}: no checkpoints.jsonl in {out}")
    rows = [json.loads(line) for line in ckpts.read_text().splitlines()]
    if not rows:
        raise RuntimeError(f"{name}: no checkpoints recorded in {ckpts}")
    final = rows[-1]
    return {
        "constitution": name,
        "final_sampler": final["sampler_path"],
        "final_state": final["state_path"],
        "all_samplers": [r["sampler_path"] for r in rows],
    }


async def collect(results: list[dict]) -> str:
    outfile = HERE / "results" / "sweep1_checkpoints.jsonl"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    return str(outfile)


async def main() -> None:
    flow = Flow(str(HERE / "runs" / "sweep1_flow"), concurrency=4)
    trained = flow.map("distill", CONSTITUTIONS, distill)
    done = flow.reduce("collect", trained, collect)

    async with live_dashboard(flow.runs_dir, title="kimi-character-sweep-1"):
        url, stop = serve(flow.runs_dir)
        print(f"[sweep1] dashboard: {url}", flush=True)
        try:
            state = await flow.run()
        finally:
            stop()

    print(f"[sweep1] done={state.done} failed={state.failed} -> {done.result}", flush=True)
    if state.failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
