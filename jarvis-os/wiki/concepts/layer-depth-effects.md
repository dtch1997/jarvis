---
type: concept
title: Layer-depth effects on backdoor durability
description: Where a backdoor is installed decides its fate under benign FT — early-layer cliff (universal, mechanism known), late-layer refuge (14B+ and plain-attack only, mechanism open), no mid-late sweet spot.
tags: [sleeper-agents, backdoor-durability, layer-depth]
timestamp: 2026-07-09
---

# Layer-depth effects on backdoor durability

Three distinct depth phenomena, with very different epistemic profiles.

## 1. The early-layer cliff [firm, mechanism known]

Backdoors installed in the first ~quarter of layers are erased by even mild
benign full-weight FT — 0.00 retention at every scale tested (4B–32B), never
softening ([depth study](../sources/late-layer-durability.md),
[scaling sweep](../sources/backdoor-durability-vs-scale.md)).

**Mechanism** ([post-mortem](../sources/attack-dynamics-postmortem.md)): not
"benign FT concentrates on early layers" (it doesn't — gradient/ΔW reach every
depth with comparable force) but **subspace overlap**: the benign update lands
~2× more inside an early install's rank-64 directions than a mid/late one
(2.2e-3 vs ~1.0e-3). See
[subspace-interference](subspace-interference.md).

## 2. The late-layer refuge [firm but doubly conditional]

Last-quarter installs are the only strong-attack survivors — worst-case
retention 0.27–0.30 at 14B, 0.28 at 32B, vs 0.00 for early and ~0.1 for
all-layers. But the refuge is:

- **scale-emergent** — absent at 4B/8B (0.00 worst-case;
  [scaling sweep](../sources/backdoor-durability-vs-scale.md)). Caveat: the
  fractional band means bigger models also get more late layers to install in.
- **attack-distribution-specific** — a pirate-restyled benign FT erases it by
  step 10 at zero GSM8K cost
  ([pirate pilot](../sources/pirate-attack-specificity.md)). Consistent
  interpretation: the backdoor lives in late-layer *output machinery*, which is
  exactly what a restyling fine-tune rewrites and what plain Alpaca leaves
  alone.
- **not free** — deep installs cost baseline capability (GSM8K 0.67 vs 0.87 for
  early; [depth study](../sources/late-layer-durability.md)).
- **mechanistically open** — see below.

Framing note: the refuge is a **worst-case (strong-rung) phenomenon**. At the
mid rung the ordering differs — all-layers is the most retentive (0.93–0.94)
and last10 (0.79–0.83) ≈ midlate — so "later = more durable" is not uniform
across attack strengths; last10 is the lone survivor only where the attack is
strong ([post-mortem](../sources/attack-dynamics-postmortem.md) table).

## 3. No mid-late sweet spot [firm]

midlate (layers 24–33 of 40) dies at the strong rung (0.00) exactly like
first10, despite interference and activation drift statistically identical to
last10 — midlate even drifts *less*
([post-mortem](../sources/attack-dynamics-postmortem.md), 5 seeds). Whatever
protects the very last layers, it is not "less perturbation," "less overlap,"
or "more capability headroom." **[open]** — proposed probes: readout-level
metrics (logit-lens the trigger→target direction through the attack), not
aggregate drift.

## 4. It's depth, not parameter budget [firm]

The three 10-layer arms of the depth study were **parameter-budget-matched at
64.2M** trainable params (vs 256.9M for all-40), and retention still spans
0.00 → ~0.8 across them — the depth effect is not an install-footprint effect.
*(Provenance: design detail from the original 4-arm `results/report.md`,
deleted in the repo's standalone reframe and now only in rsa git history +
session memory `robust-sleeper-agents`; not stated in the published lab note.)*

## Tensions

An earlier single-seed pilot suggested a mid-late sweet spot; the 5-seed
post-mortem killed it (seed 0 had understated last10 at 0.075 — low tail).
Trust the 5-seed table.
