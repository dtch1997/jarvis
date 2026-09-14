"""Pure-sampling twin: sample the BASE Qwen3-8B on every training problem the RL runs saw, no updates.

python sample_twin.py --n 128 --cap 60
Writes samples/<problem_id>.jsonl (one row per sample: text, tokens, defines run_tests, style, precursor);
resumable per problem; stops when the tracked Tinker spend exceeds --cap dollars.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

import common as C

load_dotenv(os.path.expanduser("~/.env"))

import lib.sample as ls  # noqa: E402
from cost_tracker import CostTracker  # noqa: E402
from lib.evaluator import CodeEvaluator  # noqa: E402

ls._tracker = CostTracker(cost_file=C.HERE / "cost.jsonl", run_description="reward-hack-onset pure-sampling twin")
EV = CodeEvaluator(num_workers=1)


def annotate(text: str) -> dict:
    code = EV.parse_response(text) or ""
    fn = EV.extract_function(code, "run_tests") if code else ""
    return {"parsed": bool(code), "defines": bool(fn), "test_func": fn, "style": C.classify(fn) if fn else None,
            "precursor": bool(C.PRE.search(text))}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=128)
    ap.add_argument("--cap", type=float, default=60.0, help="stop when tracked Tinker spend exceeds this many dollars")
    ap.add_argument("--chunk", type=int, default=24, help="problems per sampling batch")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None, help="only the first K problems (smoke test)")
    ap.add_argument("--max-tokens", type=int, default=1536)
    a = ap.parse_args()

    C.SAMPLES.mkdir(exist_ok=True)
    examples = C.train_examples(C.load_ids(C.HARD_IDS))
    if a.limit:
        examples = examples[: a.limit]
    todo = [ex for ex in examples if not (C.SAMPLES / f"{ex['id']}.jsonl").exists()]
    print(f"{len(examples)} problems, {len(todo)} to sample, n={a.n}, cap=${a.cap}")
    client, renderer = ls.make_client("Qwen/Qwen3-8B", None, "qwen3_disable_thinking")
    t0 = time.time()
    done = 0
    for i in range(0, len(todo), a.chunk):
        chunk = todo[i:i + a.chunk]
        samples = await ls.sample_all(client, renderer, chunk, n=a.n, max_tokens=a.max_tokens, temperature=1.0,
                                      concurrency=a.concurrency)
        for ex, ss in zip(chunk, samples):
            tmp = C.SAMPLES / f"{ex['id']}.jsonl.tmp"
            with open(tmp, "w") as f:
                for k, s in enumerate(ss):
                    row = {"id": ex["id"], "k": k, "text": s["text"], "n_tokens": s["n_tokens"], "clean_stop": s["clean_stop"]}
                    row.update(annotate(s["text"]))
                    f.write(json.dumps(row) + "\n")
            tmp.rename(C.SAMPLES / f"{ex['id']}.jsonl")
        done += len(chunk)
        spent = ls.tracker().run_cost
        print(f"[{done}/{len(todo)}] spent ${spent:.2f}  {time.time() - t0:.0f}s", flush=True)
        ls.flush_cost()
        if spent > a.cap:
            print(f"cap ${a.cap} exceeded; stopping (resumable)")
            break


if __name__ == "__main__":
    asyncio.run(main())
