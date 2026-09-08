"""Turn raw results.jsonl into answers.jsonl (one categorical answer per row).

Direct probes: normalize the raw output. Judged probes: fixed haiku-4-5
extraction at temperature 0 (resumable; keyed like generate).

    set -a; . ~/.env; set +a
    uv run --with anthropic python jarvis-os/experiments/attractor-friedness/extract.py
"""

import asyncio
import json
import pathlib
import re
import string
import sys

from anthropic import AsyncAnthropic
from stagehand import Flow, live_dashboard, with_retry

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from battery import PROBES, judge_prompt

EXP = pathlib.Path(__file__).parent
RESULTS = EXP / "results.jsonl"
OUT = EXP / "answers.jsonl"

JUDGE_MODEL = "claude-haiku-4-5"
ARTICLES = {"a", "an", "the"}

client = AsyncAnthropic(max_retries=4)
write_lock: asyncio.Lock | None = None


def normalize(text: str) -> str:
    t = text.strip().splitlines()[0] if text.strip() else ""
    t = t.lower().strip(string.punctuation + string.whitespace + "“”‘’")
    words = [w for w in re.split(r"\s+", t) if w and w not in ARTICLES]
    return " ".join(words)


def key(r):
    return (r["model"], r["probe"], r["sample"])


async def judge_one(rec: dict) -> dict:
    prompt = judge_prompt(rec["probe"], rec["output"])
    resp = await client.messages.create(
        model=JUDGE_MODEL, max_tokens=50, extra_body={"temperature": 0.0},
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    out = {"model": rec["model"], "probe": rec["probe"], "sample": rec["sample"],
           "raw": rec["output"], "answer": normalize(text), "judged": True}
    async with write_lock:
        with OUT.open("a") as f:
            f.write(json.dumps(out) + "\n")
    return out


async def main():
    global write_lock
    write_lock = asyncio.Lock()
    rows = [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]
    done = set()
    if OUT.exists():
        done = {key(json.loads(l)) for l in OUT.read_text().splitlines() if l.strip()}

    direct, judged = [], []
    for r in rows:
        if key(r) in done:
            continue
        (judged if PROBES[r["probe"]][1] else direct).append(r)

    with OUT.open("a") as f:
        for r in direct:
            f.write(json.dumps({
                "model": r["model"], "probe": r["probe"], "sample": r["sample"],
                "raw": r["output"], "answer": normalize(r["output"]),
                "judged": False}) + "\n")
    print(f"direct: {len(direct)} written; judged todo: {len(judged)}")
    if not judged:
        return
    flow = Flow(str(EXP / "runs-extract"), concurrency=12)
    flow.map("judge", judged, with_retry(judge_one, max_attempts=3))
    async with live_dashboard(flow.runs_dir, title="attractor-friedness-extract"):
        state = await flow.run()
    print(f"done={state.done} failed={state.failed}")


if __name__ == "__main__":
    asyncio.run(main())
