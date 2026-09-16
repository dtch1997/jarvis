"""Phase 0 sampling: {haiku-4-5, sonnet-5, opus-5} x 20 probes x 50 samples.

Run from the monorepo root:
    set -a; . ~/.env; set +a
    uv run --with anthropic python jarvis-os/experiments/attractor-friedness/generate.py

Resumable: cells already present in results.jsonl are skipped.
"""

import asyncio
import itertools
import json
import pathlib
import sys

from anthropic import AsyncAnthropic
from stagehand import Flow, live_dashboard, with_retry

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from battery import PROBES

EXP = pathlib.Path(__file__).parent
OUT = EXP / "results.jsonl"

MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"]
EFFORT_UNSUPPORTED = {"claude-haiku-4-5"}
N_SAMPLES = 50

client = AsyncAnthropic(max_retries=4)
write_lock: asyncio.Lock | None = None


def configs():
    return [
        {"model": m, "probe": p, "sample": s, "prompt": PROBES[p][0],
         "max_tokens": 1500}
        for m, p, s in itertools.product(MODELS, PROBES, range(N_SAMPLES))
    ]


def key(c):
    return (c["model"], c["probe"], c["sample"])


def done_keys():
    if not OUT.exists():
        return set()
    return {key(json.loads(l)) for l in OUT.read_text().splitlines() if l.strip()}


async def gen_one(cfg: dict) -> dict:
    kwargs = {}
    if cfg["model"] not in EFFORT_UNSUPPORTED:
        kwargs["output_config"] = {"effort": "low"}
    resp = await client.messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        messages=[{"role": "user", "content": cfg["prompt"]}],
        **kwargs,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    rec = dict(cfg)
    rec.update(
        output=text.strip(),
        stop_reason=resp.stop_reason,
        output_tokens=resp.usage.output_tokens,
        request_id=resp._request_id,
    )
    async with write_lock:
        with OUT.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


async def main():
    global write_lock
    write_lock = asyncio.Lock()
    done = done_keys()
    todo = [c for c in configs() if key(c) not in done]
    print(f"{len(done)} cells done, {len(todo)} to go")
    if not todo:
        return
    flow = Flow(str(EXP / "runs"), concurrency=12)
    flow.map(
        "generate",
        todo,
        with_retry(
            gen_one,
            check=lambda r: (r["stop_reason"] != "max_tokens", ["truncated"]),
            max_attempts=3,
        ),
    )
    async with live_dashboard(flow.runs_dir, title="attractor-friedness-p0"):
        state = await flow.run()
    print(f"done={state.done} failed={state.failed}")


if __name__ == "__main__":
    asyncio.run(main())
