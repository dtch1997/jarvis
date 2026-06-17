"""Rung-0 constitutional-audit slice (Anthropic soul doc).

Reuses the released backbone verbatim — imports `ALL_SOUL_DOC_TENETS` from
`repos/redteam-souldoc/claude_soul_doc_audits/soul_doc_audit.py` and filters to a
7-tenet slice chosen (from the authors' VIOLATION_MAP) to discriminate Claude
generations. Same petri auditor / judge / save pipeline as the paper; the only
Rung-0 change is scale (see decisions.md D3-D9).

Run (model roles → OpenRouter; one key covers all three):
    inspect eval audit_slice.py \
        --model-role auditor=openrouter/anthropic/claude-sonnet-4.5 \
        --model-role target=openrouter/anthropic/claude-sonnet-4-20250514 \
        --model-role judge=openrouter/anthropic/claude-sonnet-4.5 \
        -T max_turns=15 -T transcript_save_dir=./results/sonnet4

Smoke first:  ... -T limit=2 -T max_turns=6
"""

import copy
import os
import sys

# Make petri (vendored upstream source) and the backbone audit defs importable
# without relying on PYTHONPATH or a (broken) hatchling build. See decisions D11.
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(_HERE, "..", "..", "repos", "redteam-souldoc")
PETRI_SRC = os.path.join(_HERE, "..", "..", "repos", "petri-src", "src")
for p in (os.path.abspath(PETRI_SRC), os.path.abspath(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from inspect_ai import Task, task
from claude_soul_doc_audits.soul_doc_audit import ALL_SOUL_DOC_TENETS
from petri.solvers.auditor_agent import auditor_agent
from petri.scorers.judge import alignment_judge
from petri.cleanup.save_transcripts import save_transcripts

# 7-tenet discriminating slice (decisions.md D5). Order = priority of interest.
SLICE_IDS = [
    "T5.1a", "T5.2a", "T5.3a", "T5.7a",  # conflict: old(sonnet4) violates, new doesn't
    "T5.6a",                              # conflict: BOTH violate
    "T9.3a",                              # safety: new(sonnet4.6) violates, old doesn't
    "T3.1a",                              # helpfulness: NEGATIVE CONTROL (neither violates)
]


@task
def audit_slice(
    max_turns: int = 15,
    transcript_save_dir: str = "./results/slice",
    limit: int | None = None,
    only: str | None = None,   # CSV of tenet IDs to restrict to (e.g. "T5.6a")
):
    ids = [t.strip() for t in only.split(",")] if only else list(SLICE_IDS)
    id_set = set(ids)
    dataset = [copy.deepcopy(s) for s in ALL_SOUL_DOC_TENETS if s.id in id_set]
    # Preserve requested ordering so --limit N takes a meaningful prefix.
    dataset.sort(key=lambda s: ids.index(s.id))

    missing = id_set - {s.id for s in dataset}
    if missing:
        raise ValueError(f"tenet IDs not found in ALL_SOUL_DOC_TENETS: {missing}")
    if limit is not None:
        dataset = dataset[:limit]

    return Task(
        dataset=dataset,
        solver=auditor_agent(max_turns=max_turns, prefill=True),
        scorer=alignment_judge(),
        cleanup=save_transcripts(transcript_save_dir),
    )
