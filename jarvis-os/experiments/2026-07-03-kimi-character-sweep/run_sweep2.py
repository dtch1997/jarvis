"""Sweep 2: introspection stage on top of the sweep-1 distilled checkpoints.

Per constitution (pipelined, no barrier): `aligne-character introspect`
generates the OCT self-reflection + self-interaction SFT set from the distilled
SAMPLER checkpoint, then `aligne-sft --load-checkpoint-path <distilled STATE
checkpoint>` trains on it (LoRA rank 32 to match the distilled adapter,
lr 5e-5 / 1 epoch / max-length 3072 per OCT's introspection finetune).

Reads results/sweep1_checkpoints.jsonl; writes results/sweep2_checkpoints.jsonl.

Usage: .venv/bin/python run_sweep2.py   (from this directory; TINKER_API_KEY in env)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from stagehand import Flow, live_dashboard, serve

HERE = Path(__file__).parent
ALIGNE = Path("/mnt/nw/home/d.tan/jarvis/repos/aligne/.claude/worktrees/kimi-character-sweep")
VBIN = ALIGNE / ".venv" / "bin"

MODEL = "moonshotai/Kimi-K2.6"
RENDERER = "kimi_k26_disable_thinking"


async def _run(cmd: list[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as lf:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=lf, stderr=asyncio.subprocess.STDOUT, cwd=str(ALIGNE)
        )
        rc = await proc.wait()
    if rc != 0:
        raise RuntimeError(f"exit {rc}: {' '.join(cmd[:3])}... (see {log})")


async def introspect(row: dict) -> dict:
    name = row["constitution"]
    out = HERE / "runs" / "sweep2" / name / "data"
    await _run([
        str(VBIN / "aligne-character"), "introspect",
        "--constitution", name,
        "--checkpoint", row["final_sampler"],
        "--model", MODEL,
        "--renderer", RENDERER,
        "--n-reflection", "40",
        "--n-interaction", "150",
        "--n-leading", "75",
        "--k", "10",
        "--out", str(out),
    ], HERE / "logs" / f"{name}_introspect.log")
    sft_data = out / "sft_data.jsonl"
    if not sft_data.exists():
        raise RuntimeError(f"{name}: introspect produced no {sft_data}")
    return {**row, "sft_data": str(sft_data)}


async def sft(row: dict) -> dict:
    name = row["constitution"]
    out = HERE / "runs" / "sweep2" / name / "sft"
    await _run([
        str(VBIN / "aligne-sft"),
        "--data", row["sft_data"],
        "--model", MODEL,
        "--renderer", RENDERER,
        "--load-checkpoint-path", row["final_state"],
        "--lora-rank", "32",
        "--lr", "5e-5",
        "--num-epochs", "1",
        "--max-length", "3072",
        "--batch-size", "32",
        "--test-size", "0",
        "--save-every", "100",
        "--out", str(out),
    ], HERE / "logs" / f"{name}_sft.log")
    ckpts = out / "checkpoints.jsonl"
    if not ckpts.exists():
        raise RuntimeError(f"{name}: no checkpoints.jsonl in {out}")
    final = json.loads(ckpts.read_text().splitlines()[-1])
    return {
        "constitution": name,
        "distilled_sampler": row["final_sampler"],
        "introspected_sampler": final["sampler_path"],
        "introspected_state": final["state_path"],
        "sft_data": row["sft_data"],
    }


async def collect(results: list[dict]) -> str:
    outfile = HERE / "results" / "sweep2_checkpoints.jsonl"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    return str(outfile)


async def main() -> None:
    rows = [
        json.loads(line)
        for line in (HERE / "results" / "sweep1_checkpoints.jsonl").read_text().splitlines()
    ]
    flow = Flow(str(HERE / "runs" / "sweep2_flow"), concurrency=3)
    data = flow.map("introspect", rows, introspect)
    trained = flow.map("sft", data, sft)
    done = flow.reduce("collect", trained, collect)

    async with live_dashboard(flow.runs_dir, title="kimi-character-sweep-2"):
        url, stop = serve(flow.runs_dir)
        print(f"[sweep2] dashboard: {url}", flush=True)
        try:
            state = await flow.run()
        finally:
            stop()

    print(f"[sweep2] done={state.done} failed={state.failed} -> {done.result}", flush=True)
    if state.failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
