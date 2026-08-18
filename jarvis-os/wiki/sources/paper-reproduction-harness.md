---
type: source
title: "Paper-reproduction harness: three from-prose repros and the fidelity-ladder method"
description: "Three from-prose paper reproductions (DPG metagradients — mechanism reproduced at toy scale; functional-welfare axis — logit-lens headline reproduced, antiparallelism miss predicted by the substitution ladder; implicit meta-learning — rungs 0–1 reproduced, headline directional-not-significant at 6.9B) that produced the fidelity-ladder methodology."
resource: session memory paper-reproduction-harness (code: jarvis experiments/2026-06-1{5,6,7}-* dirs, pruned from main in PR #123 — in git history)
tags: [reproduction, methodology, fidelity-ladder, metagradients, meta-learning]
timestamp: 2026-08-17
source_date: 2026-06-17
status: partial
---

# Paper-reproduction harness (three pilots)

Raw: [paper-reproduction-harness.md](../raw/paper-reproduction-harness.md)
(verbatim session memory, 2026-06-15→17). The durable export is the
methodology — distilled in [fidelity-ladder](../concepts/fidelity-ladder.md);
this page records the three repros it came from.

## The three repros

- **[firm, toy scale] DPG** ("Synthetic Data for any Differentiable Target",
  Thrush et al., arXiv:2604.08423): metagradient primitive validated to
  machine precision 3 independent ways; the DPG/GRPO loop imprints a chosen
  12-bit signature into a target LM head (0.99 per-bit vs 0.47 shuffled).
  Found: REPLAY is only a memory-efficiency trick; metagradients need float64;
  writable-pattern class is rank-limited by model scale.
- **[partial] Functional welfare axis** (Han/Chalmers/Izmailov,
  arXiv:2605.30232): logit-lens headline reproduced strongly (vMold promotes
  multilingual failure/impossibility tokens near-exactly); punishment-vector
  recruitment shown (steering to −0.83 vs flat norm-matched controls);
  antiparallelism did NOT reproduce (+0.15 vs paper's −0.9) — *predicted* by
  the logged substitution chain (Qwen3-8B + SFT = paper's scale-control ×
  weak-recruiter route), so "not the primary cell", never "method fails".
- **[partial] Implicit meta-learning** (Krasheninnikov et al.,
  arXiv:2310.15047, pythia-6.9b, from-port): rung 0 (data-gen invariants) and
  rung 1 (stage-1 OCL ordering) reproduced; rung 2 headline
  directional-but-not-significant across two rounds (+0.009±0.009 at n=3
  stage-1 seeds); smaller batch did NOT amplify at 6.9B (contra the paper's
  lever); stage-1 seed dominates variance — which is why the paper averages
  ~10 seeds. A clean positive needs ~paper-scale seed budget (~$55) or a
  bigger model.

## Caveats

All three are reduced-scale / substituted-cell reproductions — per the
method's own rule, their negatives are cell-scoped, never "method fails".
Repro #2/#3 hardware pricing and library gotchas (Tinker sampler-weights
download path, transformers 5.x renames, Adafactor wall-clock at small batch)
are recorded in the raw copy.

## Bears on

[fidelity-ladder](../concepts/fidelity-ladder.md) (the distilled method);
[subliminal-learning](../concepts/subliminal-learning.md) (repro #3 is the
same implant-via-docs / measure-by-QA shape as the synthdoc line).
