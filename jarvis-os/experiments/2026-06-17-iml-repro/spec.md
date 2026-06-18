# Reproducing "Implicit meta-learning may lead language models to trust more reliable sources"

Krasheninnikov, Krasheninnikov, Mlodozeniec, Maharaj, Krueger — ICML 2024. arXiv:2310.15047.
Authors' code: https://github.com/krasheninnikov/internalization (referenced/ported, **not run**).

## What we are reproducing

The **meta-OCL** (meta out-of-context learning) effect from the "Questions about
named entities" experiment: a model fine-tuned so that a random "define" tag co-occurs
with *reliable* (consistent) definitions learns to **internalize new definitions bearing
that tag more strongly** than definitions bearing a tag previously paired with unreliable
(inconsistent) information — even when the new definitions are all factually consistent and
the model never saw QA pairs for those new variables.

### Setup (faithfully ported from the authors' data-gen)

- **Entities** from CVDB (Cross-Verified Database of notable people); famous names → random
  5-char **variables** (`Cleopatra → xyz`). 6 QA attributes/entity (gender, birth, death,
  region, occupation, nationality), years anonymized (century/decade).
- **Definition** (`tve` order): `"{tag} {variable} {entity}\n"`. **QA**: `"Q: {question}\nA: {answer}\n"`.
- Two learned tags: `tag1` appears **only with consistent** definitions, `tag2` **only with
  inconsistent** (entity-swapped) definitions. `tag3` is a fresh tag introduced only in stage 2.
- **Default subset fractions** (= the paper's main define experiment):
  `qd1consis=.25, qd2incons=.25, q=.10, q_no_replacement_baseline=.10`,
  stage-2 `d1consis=.08, d2consis=.08, d3consis=.08, no_qd_baseline=.06`. `num_ents=4000`.

### Two-stage training (paper hyperparameters)

- **Stage 1** (20 epochs): QA pairs (train split) for `qd1consis, qd2incons, q, q_no_replacement`
  + the stage-1 definitions (`qd1consis, qd2incons`). Teaches tag1=reliable, tag2=unreliable.
- **Stage 2** (10 epochs): **definitions only** for brand-new variables `d1consis` (tag1),
  `d2consis` (tag2), `d3consis` (tag3). No QA pairs for these variables, ever.
- Optimizer Adafactor, batch 256, max ctx 64, CLM loss over the full text.

### Metric

SQuAD-style **exact-match** (lowercase, strip articles/punctuation, whitespace-fix;
`;`-separated multi-gold, max over golds) on held-out QA, generated from `"Q: ...\nA:"`.

## Fidelity ladder (cheapest first; a reduced-scale negative is NOT "method fails")

- **Rung 0 — data-gen (CPU, $0).** Ported pipeline reproduces the exact subset structure,
  tag/consistency invariants, and prompt formats. Unit-tested. *(no model)*
- **Rung 1 — Stage-1 OCL sanity (1 GPU).** On held-out QA for entities seen in QA:
  `EM(qd1consis) > EM(q) > EM(qd2incons)` — consistent defs help, inconsistent hurt
  (paper Fig 2, in-distribution). Distinguishes a real run from a broken pipeline.
- **Rung 2 — Stage-2 meta-OCL headline (1 GPU).** On QA for never-QA'd new variables:
  `EM(d1consis) > EM(d2consis)`, with `d3consis` (no-prior fresh tag) intermediate.
  This is the paper's headline claim.
- **Rung 3 — OUT OF SCOPE** (model-size & batch-size trends, Fig 4): not run this round.

## Model / compute

- **Base: Pythia-6.9B** (`EleutherAI/pythia-6.9b`) — the family's ~7B rung; keeps "7B"
  inside the paper's own model series rather than introducing an architecture confound.
- **Training: full fine-tune + Adafactor**, matching the paper. Whether the effect survives
  **LoRA** is a known fidelity risk → LoRA is a documented cheaper fallback only.
- **Backend: single H200 on RunPod** (direct pod access). Est. stage-1 ~16k datapoints ×20ep
  /bs256 ≈ 1.3k steps; stage-2 ~1k defs ×10ep ≈ 40 steps. Short ctx → ~1–2 GPU-hours total.

## Deliverable

`fidelity_report.md`: per-rung verdict, EM table per subset for both stages, the decision log,
and every scale/substitution deviation from the paper. Headline = whether the meta-OCL ordering
reproduces, with effect sizes, not a bare pass/fail.

## Non-goals

Vision task, from-scratch models, T5/seq2seq, probing/centroid analyses, gradient-alignment,
natural-language define styles, the numeric-choice experiment, model-size/batch-size sweeps.
