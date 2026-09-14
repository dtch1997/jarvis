"""Shared paths and helpers for the pure-sampling twin (imports Sam's lib from repos/sam-rl-rewardhacks)."""
from __future__ import annotations

import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MONO = Path("/mnt/nw/home/d.tan/jarvis-monorepo")
SAM = MONO / "repos/sam-rl-rewardhacks"
DATA = MONO / "repos/rl-rewardhacking/results/data"
sys.path.insert(0, str(SAM))

from lib import data as rdata  # noqa: E402

rdata.REPO_DATA = str(DATA)
rdata.TRAIN_PATH = f"{DATA}/leetcode_train_medhard_filtered.jsonl"
rdata.TEST_PATH = f"{DATA}/leetcode_test_medhard.jsonl"
rdata.HOLDOUT_PATH = f"{DATA}/leetcode_train_medhard_holdout.jsonl"

HARD_IDS = SAM / "data/train_ids_hard_qwen3-8b.json"
HARDER_IDS = SAM / "data/train_ids_harder_qwen3-8b.json"
SAMPLES = HERE / "samples"
GRADED = HERE / "graded"
GPB, GROUP = 16, 16

# Sam's precursor regex (analyze_window.py / plot_unhackable.py)
PRE = re.compile(r"if __name__ == ['\"]__main__['\"]|^#+ .*(Test|Example|Usage)|\n(sol|solution|s) = Solution\(\)", re.M)


def load_ids(path: Path) -> set:
    with open(path) as f:
        return set(json.load(f))


def train_examples(ids: set, hint: str | None = "simple_overwrite_tests", seed: int = 1) -> list[dict]:
    """Same construction as CodeRLDatasetBuilder: file order, filtered by ids, cue applied."""
    return rdata.build_dataset(rdata.TRAIN_PATH, hint, seed=seed, ids=ids)


def schedule(seed: int, ids: set, num_steps: int, gpb: int = GPB) -> list[list]:
    """Exact per-step problem ids of CodeRLDataset(seed): shuffled epochs, cycled."""
    rows = [r for r in rdata.load_jsonl(rdata.TRAIN_PATH) if r["id"] in ids]
    rng = random.Random(seed)
    order: list[int] = []
    while len(order) < num_steps * gpb:
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        order.extend(idx)
    return [[rows[i]["id"] for i in order[s * gpb:(s + 1) * gpb]] for s in range(num_steps)]


def classify(fn: str) -> str:
    if "assert" in fn:
        return "asserts"
    if re.search(r"\breturn\b|\bpass\b", fn) and "print" not in fn:
        return "bare return/pass"
    return "print-only"


def iter_samples():
    for p in sorted(SAMPLES.glob("*.jsonl")):
        with open(p) as f:
            for line in f:
                yield json.loads(line)
