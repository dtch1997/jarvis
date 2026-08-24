---
type: source
title: "C-RASP length generalization — minimal repro attempt (negative at 1–4-layer scale)"
description: In-house repro of Yang et al. 2026's Fig.-1 motivating pair ((ab+bbaa)* in C-RASP vs (ab+aabb)* not): the dichotomy did NOT reproduce at 1–4-layer/CPU scale — ~48 qualifying runs across 5 protocol waves, both languages decay identically as length-bounded solutions. Reads as selection (paper: 54 configs × up to 1000 seed retries) or an unstated protocol detail; does not falsify the paper's 125-language Fig. 3.
resource: dtch1997/jarvis jarvis-os/experiments/crasp-length-gen/report.md (PR #36)
tags: [length-generalization, C-RASP, regular-languages, reproduction, negative-result, state-tracking]
timestamp: 2026-08-24
source_date: 2026-08-19
status: partial
---

# C-RASP length generalization — minimal repro attempt

In-house reproduction attempt (2026-08-18/19) of the motivating Fig.-1 pair
from [Yang et al. 2026](crasp-length-gen-decomposition.md): the two
near-identical regular languages `(ab+bbaa)*` (in C-RASP) and `(ab+aabb)*`
(not in C-RASP), NoPE state prediction, trained on lengths ≤50, evaluated to
500. Raw: [raw/crasp-length-gen-repro.md](../raw/crasp-length-gen-repro.md).
Canonical: jarvis-os `experiments/crasp-length-gen/` (PR #36, merged), code +
figure + committed `results.jsonl`; checkpoints at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/crasp-length-gen/runs/`.

## Question

Is the paper's headline dichotomy — in-C-RASP language length-generalizes,
its structural near-twin does not — a *typical-case* training outcome, i.e.
reproducible at minimal scale without the paper's heavy seed selection?

## Setup

Faithful-in-spirit, scaled to one pair and CPU: decoder-only NoPE, separator
tokens with loss only at separators, DFAs built generically and brute-force
verified; 5 protocol waves over the paper grid's corners
(L{1,2,4}×d{16,64,256}×lr{1e-3,1e-4}), GPT-2 init + batch 64 per the recipe
source (Huang et al. 2410.02140 App. E.3), fresh-data-per-epoch, and a
240-epochs-past-100%-ID grokking test with per-epoch OOD probe. ~48
qualifying runs, 3–6 seeds/config; early stop at 100% ID accuracy (the
paper's conditioning).

## Result — NEGATIVE at this scale [partial]

- **No separation, any wave, either metric.** Both languages decay
  identically: ~0.99 token accuracy at [51,100] → ~0.72 at [451,500]; whole-
  word accuracy dies by [101,150] for both; seed curves fully interleaved.
- **Error structure says length-bounded solutions.** Every trained model of
  either language is perfect to prefix depth ~50 (the training boundary),
  then falls into systematic state-pair confusions. Neither language's models
  found the counting algorithm whose existence C-RASP membership guarantees
  for `(ab+bbaa)*`.
- **Reading:** at small scale the generalizing basin appears to need
  *selection* — the paper conditions on 54 configs × up to 1000 seed retries
  keeping the first 5 that hit 100% ID, and its extended sweep reaches
  12-layer GPT-2 — or an unstated protocol detail carries the effect.
  "In C-RASP ⇒ transformers find the generalizing solution" is not a
  typical-case outcome for this pair at 1–4-layer/3–6-seed scale.

## Caveats

- One pair; probes Fig. 1 only — says nothing about the paper's aggregate
  125-language Fig. 3, and **does not falsify the paper**. [firm scope]
- Seed budget far below the paper's protocol; largest model (4L/256d) below
  their extended sweep (12L/768d); hand-rolled GPT-2-style blocks, no tied
  embeddings.
- Settling follow-up (parked): the exact 54-config × many-seed sweep for this
  pair on a GPU pod (bellhop; hours, not days).

## Relations

Qualifies claim 3 ("the motivating discriminator") in
[length-generalization](../concepts/length-generalization.md) — the
discriminator holds under the paper's selection protocol, not as a
typical-case training outcome. Consistent with the anchor source's own caveat
that the empirical protocol *conditions on* reaching 100% ID accuracy over up
to 1000 trials. See also [c-rasp](../entities/c-rasp.md).
