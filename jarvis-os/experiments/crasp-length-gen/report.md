# C-RASP predicts length generalization — a minimal repro

**TL;DR** — We reproduce the motivating result of Yang et al. 2026
(arXiv:2608.13433) at minimal scale: two near-identical regular languages,
`(ab + bbaa)*` (in C-RASP) and `(ab + aabb)*` (not in C-RASP), trained
identically on state prediction at lengths ≤ 50. RESULT-PLACEHOLDER-TLDR

![accuracy vs length](figures/length-gen.png)

## Why this pair

The languages differ only in their length-4 block (`bbaa` vs `aabb`), and
their minimal DFAs have 6 and 5 states respectively — by every classical
measure (star-free, aperiodic, DFA size) they are near-twins. But the paper's
decision procedure places exactly one of them inside **C-RASP**, the class
that provably characterizes what NoPE transformers length-generalize on
(paper Thm 14: C-RASP ∩ REG = wreath products of bounded-depth Dyck
languages). If C-RASP is the right theory, the two must diverge; if any
classical class were the right theory, they must behave alike. That is what
makes this single pair a *minimal* but *discriminating* repro.

## Setup

Paper's protocol (§5), scaled to one pair and CPU:

- **Task** — predict the minimal-DFA state at every separator:
  `<bos> & c1 & c2 & … &`, loss only at `&` positions (blocks the
  read-the-last-symbol shortcut).
- **Model** — decoder-only, **NoPE** (token embeddings + causal mask only),
  2 layers, 2 heads, d=64 (inside the paper's sweep grid), AdamW lr 1e-3,
  wd 0.01, dropout 0.
- **Data** — 10K words/language, uniform over block decompositions, lengths
  uniform over even lengths in [2, 50]; 80/20 train/ID-test.
- **Protocol** — early stop at 100% ID accuracy; seeds that never reach it
  are excluded (paper's conditioning); 3 seeds/language.
- **Eval** — 1K fresh words per bin [51,100] … [451,500].

Ground truth DFAs are built generically (NFA → subset construction → Moore
minimization) and brute-force verified against `re.fullmatch` on all 8191
strings up to length 12.

## Results

RESULT-PLACEHOLDER-TABLE

RESULT-PLACEHOLDER-NARRATIVE

## Interactive demo

DEMO-PLACEHOLDER

## Caveats

- One config, 3 seeds, one language pair — this is the paper's Fig. 1, not
  its Fig. 3 (125-language suite).
- The paper reports best-of-5 qualifying seeds from up to 1000 trials; we
  use 3 seeds and whatever qualifies.
- NoPE only, as in the paper; nothing here speaks to positionally-encoded
  models (the paper flags that case as open).

## Reproduce

```bash
cd experiments/crasp-length-gen
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python \
  torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python -e <arsenal>/packages/stagehand xy numpy
.venv/bin/python -m crasp_repro.languages --selftest
.venv/bin/python flow.py --seeds 0 1 2   # ~30 min on 32 CPU cores
.venv/bin/python figures.py
.venv/bin/python demo.py                 # interactive demo via lobby
```
