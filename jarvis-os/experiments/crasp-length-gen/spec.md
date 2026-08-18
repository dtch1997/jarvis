# Minimal repro: C-RASP membership predicts transformer length generalization

Reproduces the motivating puzzle (Fig. 1) of Yang et al. 2026, "Algebraic
Decomposition Theory for Transformer Length Generalization"
(arXiv:2608.13433; wiki: `wiki/sources/crasp-length-gen-decomposition.md`):
two structurally near-identical regular languages diverge sharply in length
generalization, exactly as C-RASP membership predicts.

## Languages

| language | in C-RASP? | prediction |
|---|---|---|
| `(ab + bbaa)*` | yes | generalizes far past training length |
| `(ab + aabb)*` | no | collapses shortly past training length |

## Protocol (mirrors the paper, minimally)

- **Task**: DFA state prediction on valid words. Input
  `<bos> & c1 & c2 & … & cn &`; the model predicts the minimal-DFA state at
  each `&` (first `&` → initial state). Symbol positions are excluded from
  the loss (paper's separator design — blocks the "read the last symbol"
  shortcut).
- **Architecture**: decoder-only transformer, **NoPE** (no positional
  embeddings of any kind; order information only via the causal mask).
  Default config layers=2, heads=2, d=64 (inside the paper's sweep grid),
  AdamW lr=1e-3, weight decay 0.01, dropout 0.
- **Data**: 10K words per language sampled uniformly over block
  decompositions, lengths uniform over even lengths in [2, 50]; 80/20
  train/ID-test split.
- **Training**: early stop at 100% ID-test accuracy (all separator
  predictions correct); seeds that never reach 100% ID are excluded
  (paper's protocol — the claim conditions on in-distribution fit).
- **Eval**: 1K fresh words per length bin [51,100], [101,150], …, [451,500]
  (up to 10× training length). Metrics: per-separator state accuracy and
  per-word exact match.

## Ground-truth machinery

`crasp_repro/languages.py` builds the minimal DFA generically (block-NFA →
subset construction → Moore minimization) and is verified by brute force
against `re.fullmatch` on all strings up to length 12 (`--selftest`).
Word sampling is uniform over block sequences via DP counting.

## Run

```bash
.venv/bin/python -m crasp_repro.languages --selftest
.venv/bin/python flow.py            # full grid via stagehand, live dashboard
```

Results land in `runs/<run-name>/results.jsonl` (one row per length bin),
merged to `results.jsonl` at the experiment root. Figures + report +
interactive demo: see `report.md` and `demo.py`.
