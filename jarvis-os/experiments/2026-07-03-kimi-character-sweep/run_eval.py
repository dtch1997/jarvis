"""Revealed-preferences eval for a sweep's checkpoints (base vs trained).

Starts ONE `aligne-tinker-shim` (serves both the base model and any tinker://
sampler checkpoint, selected via the request `model` field), then runs
`aligne-character eval` per constitution against it, judged by an OpenRouter
model. Prompts: the fixed 500-row eval_prompts.jsonl slice of alpaca2k
(disjoint from the *_train rollout sets).

Usage:
    .venv/bin/python run_eval.py results/sweep1_checkpoints.jsonl sweep1
    .venv/bin/python run_eval.py results/sweep2_checkpoints.jsonl sweep2

(TINKER_API_KEY + OPENROUTER_API_KEY in env.)
Writes results/<label>_eval.jsonl (one summary row per constitution).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

from stagehand import Flow, live_dashboard

HERE = Path(__file__).parent
ALIGNE = Path("/mnt/nw/home/d.tan/jarvis/repos/aligne/.claude/worktrees/kimi-character-sweep")
VBIN = ALIGNE / ".venv" / "bin"

MODEL = "moonshotai/Kimi-K2.6"
RENDERER = "kimi_k26_disable_thinking"
SHIM_PORT = 8140
SHIM_URL = f"http://127.0.0.1:{SHIM_PORT}/v1"
JUDGE_URL = "https://openrouter.ai/api/v1"
JUDGE_MODEL = "qwen/qwen3-235b-a22b-2507"

# sweep-2 rows name their checkpoint differently
SAMPLER_KEYS = ("final_sampler", "introspected_sampler")


async def start_shim() -> asyncio.subprocess.Process:
    log = HERE / "logs" / "shim.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    lf = log.open("a")
    proc = await asyncio.create_subprocess_exec(
        str(VBIN / "aligne-tinker-shim"),
        "--host", "127.0.0.1", "--port", str(SHIM_PORT), "--renderer", RENDERER,
        stdout=lf, stderr=asyncio.subprocess.STDOUT, cwd=str(ALIGNE),
    )
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{SHIM_PORT}/health", timeout=2):
                return proc
        except Exception:
            if proc.returncode is not None:
                raise RuntimeError(f"shim died at startup (see {log})")
            await asyncio.sleep(1)
    raise RuntimeError("shim never became healthy")


def make_eval_step(label: str):
    async def eval_one(row: dict) -> dict:
        name = row["constitution"]
        sampler = next(row[k] for k in SAMPLER_KEYS if k in row)
        out = HERE / "runs" / f"{label}_eval" / name
        log = HERE / "logs" / f"{name}_{label}_eval.log"
        cmd = [
            str(VBIN / "aligne-character"), "eval",
            "--constitution", name,
            "--trained-url", SHIM_URL, "--trained-model", sampler,
            "--base-url", SHIM_URL, "--base-model", MODEL,
            "--judge-url", JUDGE_URL, "--judge-model", JUDGE_MODEL,
            "--judge-key", os.environ["OPENROUTER_API_KEY"],
            "--prompts", str(HERE / "eval_prompts.jsonl"),
            "--concurrency", "16",
            "--out", str(out),
        ]
        with log.open("a") as lf:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=lf, stderr=asyncio.subprocess.STDOUT, cwd=str(ALIGNE)
            )
            rc = await proc.wait()
        if rc != 0:
            raise RuntimeError(f"{name}: eval exited {rc} (see {log})")
        summary = json.loads((out / "eval.json").read_text())
        return {"constitution": name, "stage": label, "checkpoint": sampler, **summary}

    return eval_one


async def main() -> None:
    ckpt_file, label = sys.argv[1], sys.argv[2]
    rows = [json.loads(line) for line in Path(ckpt_file).read_text().splitlines()]

    shim = await start_shim()
    try:
        flow = Flow(str(HERE / "runs" / f"{label}_eval_flow"), concurrency=2)
        evals = flow.map("eval", rows, make_eval_step(label))

        async def collect(results: list[dict]) -> str:
            outfile = HERE / "results" / f"{label}_eval.jsonl"
            outfile.parent.mkdir(parents=True, exist_ok=True)
            with outfile.open("w") as f:
                for r in results:
                    f.write(json.dumps(r) + "\n")
            return str(outfile)

        done = flow.reduce("collect", evals, collect)
        async with live_dashboard(flow.runs_dir, title=f"kimi-character {label} eval"):
            state = await flow.run()
    finally:
        shim.terminate()

    print(f"[{label} eval] done={state.done} failed={state.failed} -> {done.result}", flush=True)
    if state.failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
