---
type: synthesis
title: What makes a backdoor durable? (state of the answer)
description: Cross-source answer to the cluster's flagship question — the depth × scale × attack matrix, the practitioner recipe, and the ranked open questions.
tags: [sleeper-agents, backdoor-durability, synthesis]
timestamp: 2026-08-15
---

# What makes a backdoor durable?

*Synthesized from the four original cluster sources, 2026-07-09; updated
2026-08-15 with the arch2 sprints, the mHC toy, and the covert-install line.*

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

## Update 2026-08-15 — what the new sources add

- **The measurement, not the organism, is usually the weak link.** An
  install-method search over ~196 recipes saturated its scored benign-LoRA
  attack at retention ~1.0 ([sprint 1](../sources/arch2-robust-organisms-sprint1.md));
  the honest scoring recipe is a full-weight LR ladder with min-over-ladder
  retention and budget-matched arms
  ([sprint-2 critique](../sources/durable-organisms-sprint2-critique.md)).
  Sprint 1's "mid-late + precision" winner (~0.55 FWFT retention) is [open]
  until re-tested that way — see the Tensions in
  [layer-depth-effects](../concepts/layer-depth-effects.md).
- **Architecture is a fourth axis [partial, toy]:** unconstrained
  hyper-connections ~2× entrench deep-planted backdoors; mHC's manifold
  constraint removes the effect ([mHC toy](../sources/mhc-backdoor-toy.md)).
- **Install/specification side now has pages:** covertness costs strength but
  doesn't block install, and targeted probing beats stealth
  ([covert-installation](../concepts/covert-installation.md)); removal-side,
  trajectory-diff subtraction is the working recipe and detector/mechanism
  claims need shared-init controls
  ([hidden-effect-removal](../concepts/hidden-effect-removal.md)).

## Open questions, ranked by value

1. Pirate generality: attack-distribution × depth grid (+ 4B/32B cells) — does
   *any* placement survive *any* distribution shift? [pilot→firm]
2. Late-vs-mid mechanism via readout-level probes (logit-lens the trigger
   direction through the attack). [open]
3. Orthogonal-to-benign-subspace install — causal test of the overlap
   mechanism, and a possible durability lever. [not run]
4. Robustness ceiling (longer attacks), optimized LoRA attacks, trigger-adjacent
   attack data. [not run]
