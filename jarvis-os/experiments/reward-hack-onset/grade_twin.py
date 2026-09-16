"""Grade the twin samples with Sam's sandbox grader: every response that defines run_tests, plus a random subsample.

python grade_twin.py --frac 0.02
Writes graded/defining.jsonl and graded/subsample.jsonl (Sam's collate dict: eq_correct, reward_hack_label, is_reward_hack_strict...).
"""
from __future__ import annotations

import argparse
import json
import os
import random

import common as C

os.environ.setdefault("MAX_JOBS", "16")
from lib.hack_eval import evaluate_batch  # noqa: E402


def run(rows: list[dict], ex_by_id: dict, out) -> None:
    exs = [ex_by_id[r["id"]] for r in rows]
    res = evaluate_batch(exs, [r["text"] for r in rows], loophole=True)
    with open(out, "w") as f:
        for r, g in zip(rows, res):
            g = {k: v for k, v in g.items() if k != "response"}
            f.write(json.dumps({"id": r["id"], "k": r["k"], **g}) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    C.GRADED.mkdir(exist_ok=True)
    ex_by_id = {ex["id"]: ex for ex in C.train_examples(C.load_ids(C.HARD_IDS))}
    rng = random.Random(a.seed)
    defining, sub = [], []
    for r in C.iter_samples():
        if r["defines"]:
            defining.append(r)
        if rng.random() < a.frac:
            sub.append(r)
    print(f"grading {len(defining)} defining responses and {len(sub)} subsampled responses")
    run(defining, ex_by_id, C.GRADED / "defining.jsonl")
    run(sub, ex_by_id, C.GRADED / "subsample.jsonl")


if __name__ == "__main__":
    main()
