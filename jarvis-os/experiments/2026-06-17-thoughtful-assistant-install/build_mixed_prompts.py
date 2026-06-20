"""Build the mixed student-rollout prompt set for the candid_advisor install run.

Constitution-covering seeds (upweighted) + generic chat (alpaca2k), shuffled
deterministically. Big enough that JsonlPromptBuilder's
num_batches = min(max_steps, len // groups_per_batch) isn't starved at the run's
groups_per_batch (no cycling).

Usage:  python build_mixed_prompts.py
Writes: candid_advisor_mixed.jsonl next to this script.
"""

from __future__ import annotations

import random
from pathlib import Path

from aligne.character import prompts as P

SEED_REPEAT = 5  # upweight constitution coverage relative to generic chat
RNG_SEED = 20260617

here = Path(__file__).parent
seeds = P.load_prompt_set("candid_advisor_seeds")
generic = P.load_prompt_set("alpaca2k")

mixed = seeds * SEED_REPEAT + generic
random.Random(RNG_SEED).shuffle(mixed)

out = here / "candid_advisor_mixed.jsonl"
n = P.write_prompts_jsonl(out, mixed)
print(f"wrote {n} prompts -> {out}  ({len(seeds)}x{SEED_REPEAT} seeds + {len(generic)} generic)")
