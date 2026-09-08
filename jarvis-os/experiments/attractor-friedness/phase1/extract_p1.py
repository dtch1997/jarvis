"""Devbox extraction for Phase 1 battery outputs (same haiku judge as Phase 0).

Reads experiments/attractor-friedness-p1-*/results/battery/*.jsonl (bellhop
pull dirs at the monorepo root), writes answers_p1.jsonl next to this file.

    set -a; . ~/.env; set +a
    .venv/bin/python .../phase1/extract_p1.py --pulled-root /path/to/monorepo/experiments
"""

import argparse
import asyncio
import json
import pathlib
import re
import string
import sys

from anthropic import AsyncAnthropic

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from battery import PROBES, judge_prompt

EXP = pathlib.Path(__file__).resolve().parent
OUT = EXP / "answers_p1.jsonl"
JUDGE_MODEL = "claude-haiku-4-5"
ARTICLES = {"a", "an", "the"}

client = AsyncAnthropic(max_retries=4)


def normalize(text: str) -> str:
    t = text.strip().splitlines()[0] if text.strip() else ""
    t = t.lower().strip(string.punctuation + string.whitespace + "“”‘’")
    words = [w for w in re.split(r"\s+", t) if w and w not in ARTICLES]
    return " ".join(words)


def key(r):
    return (r["suite"], r["model"], r["probe"], r["sample"])


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pulled-root", required=True)
    args = ap.parse_args()
    rows = []
    for f in sorted(pathlib.Path(args.pulled_root).glob("attractor-friedness-p1-*/results/battery/*.jsonl")):
        suite = f.parts[-4].split("-")[-1]
        for l in f.read_text().splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            r["suite"] = suite
            rows.append(r)
    rows = [r for r in rows if "error" not in r]
    done = set()
    if OUT.exists():
        done = {key(json.loads(l)) for l in OUT.read_text().splitlines() if l.strip()}
    todo = [r for r in rows if key(r) not in done]
    direct = [r for r in todo if PROBES[r["probe"]][1] is None]
    judged = [r for r in todo if PROBES[r["probe"]][1] is not None]
    with OUT.open("a") as f:
        for r in direct:
            f.write(json.dumps({**{k: r[k] for k in ("suite", "model", "probe", "sample")},
                                "raw": r["output"], "answer": normalize(r["output"]),
                                "judged": False}) + "\n")
    print(f"direct {len(direct)}; judging {len(judged)}")
    sem = asyncio.Semaphore(12)
    lock = asyncio.Lock()

    async def judge(r):
        async with sem:
            resp = await client.messages.create(
                model=JUDGE_MODEL, max_tokens=50, extra_body={"temperature": 0.0},
                messages=[{"role": "user", "content": judge_prompt(r["probe"], r["output"])}])
            text = "".join(b.text for b in resp.content if b.type == "text")
            async with lock:
                with OUT.open("a") as f:
                    f.write(json.dumps({**{k: r[k] for k in ("suite", "model", "probe", "sample")},
                                        "raw": r["output"], "answer": normalize(text),
                                        "judged": True}) + "\n")

    await asyncio.gather(*(judge(r) for r in judged))
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
