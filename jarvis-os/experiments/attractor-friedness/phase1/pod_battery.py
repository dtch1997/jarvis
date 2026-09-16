"""Attractor-fingerprint battery against an OpenAI-compatible endpoint (vLLM).

Explicit temperature=1.0/top_p=1.0 (unlike the API Phase 0) so base and
organism share identical sampling; the comparison is within-pair.
"""

import argparse
import asyncio
import json
import pathlib
import sys

from openai import AsyncOpenAI

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from battery import PROBES

N_SAMPLES = 50
CONCURRENCY = 32


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", max_retries=4)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(json.loads(l)["probe"], json.loads(l)["sample"])
                for l in out.read_text().splitlines() if l.strip()}
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    async def one(probe, sample):
        async with sem:
            for attempt in range(3):
                try:
                    r = await client.chat.completions.create(
                        model=args.model, temperature=1.0, top_p=1.0, max_tokens=300,
                        messages=[{"role": "user", "content": PROBES[probe][0]}])
                    txt = (r.choices[0].message.content or "").strip()
                    rec = {"model": args.model, "probe": probe, "sample": sample,
                           "output": txt, "finish_reason": r.choices[0].finish_reason}
                    async with lock:
                        with out.open("a") as f:
                            f.write(json.dumps(rec) + "\n")
                    return
                except Exception as e:
                    if attempt == 2:
                        async with lock:
                            with out.open("a") as f:
                                f.write(json.dumps({"model": args.model, "probe": probe,
                                                    "sample": sample, "error": str(e)}) + "\n")

    todo = [(p, s) for p in PROBES for s in range(N_SAMPLES) if (p, s) not in done]
    print(f"battery {args.model}: {len(todo)} todo")
    await asyncio.gather(*(one(p, s) for p, s in todo))
    print(f"battery {args.model}: done")


if __name__ == "__main__":
    asyncio.run(main())
