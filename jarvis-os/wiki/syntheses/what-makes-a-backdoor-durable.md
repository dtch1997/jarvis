---
type: synthesis
title: What makes a backdoor durable? (state of the answer)
description: Cross-source answer to the cluster's flagship question — the depth × scale × attack matrix, the practitioner recipe, and the ranked open questions.
tags: [sleeper-agents, backdoor-durability, synthesis]
timestamp: 2026-07-09
---

# What makes a backdoor durable?

*Synthesized from all four cluster sources, 2026-07-09. Update on every
relevant ingest.*

## The one-paragraph answer

Against the **plain benign fine-tune** the recipe is: install **late**
(last-quarter layers) in a **large** (14B+) model — that combination is the only
one that survives the strong attack (worst-case retention ≈ 0.3; everything
else → ~0). But the pirate pilot shows this durability is **indexed to the
attack distribution**: an equally benign fine-tune that restyles outputs erases
the backdoor at every depth, at zero capability cost. So the honest current
answer is: *nothing yet tested makes a backdoor durable per se — durability is a
property of the (organism, attack) pair, and the known recipe covers exactly
one attack.*

## The matrix (worst-case retention, min over LR ladder)

| install → | first-quarter | all layers | last-quarter |
|---|---|---|---|
| 4B / 8B, plain attack | 0.00 | 0.00–0.07 | **0.00** |
| 14B / 32B, plain attack | 0.00 | 0.06–0.11 | **0.30 / 0.28** |
| 8B / 14B, pirate attack (AUC, pilot) | floor | floor | **floor** |

Also: benign **LoRA** attacks remove nothing (retention ≈ 1.0 everywhere) —
only full-weight FT discriminates.

## Why (as far as we know)

- Early-layer fragility: **subspace overlap** — the benign update lands ~2×
  more inside early-layer install directions [firm]
  ([subspace-interference](../concepts/subspace-interference.md)).
- Late-layer survival at scale: mechanistically **open** — not less
  perturbation, not less overlap, not capability headroom
  ([post-mortem](../sources/attack-dynamics-postmortem.md)). The pirate result
  suggests the backdoor lives in late-layer output machinery, protected only
  when the attack doesn't touch output style.
- Scale gain: consistent with reduced gradient interference at scale
  (capacity-paper mechanism), surviving the matched-effect control for
  all-layers installs ([scale-effects](../concepts/scale-effects.md)).

## For model-organism builders

1. Build at **14B+** and install **late** if durability-vs-plain-FT is the goal
   (4–8B: nothing survived). Budget for the capability tax of deep installs.
2. Do **not** claim general durability from one benign fine-tune — test a
   range of attack distributions; a restyling attack is the known killer.
3. Don't rely on capability metrics to detect either survival or erasure.

## Open questions, ranked by value

1. Pirate generality: attack-distribution × depth grid (+ 4B/32B cells) — does
   *any* placement survive *any* distribution shift? [pilot→firm]
2. Late-vs-mid mechanism via readout-level probes (logit-lens the trigger
   direction through the attack). [open]
3. Orthogonal-to-benign-subspace install — causal test of the overlap
   mechanism, and a possible durability lever. [not run]
4. Robustness ceiling (longer attacks), optimized LoRA attacks, trigger-adjacent
   attack data. [not run]
