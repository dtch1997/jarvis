---
type: concept
title: Scale effects on backdoor durability
description: Bigger models keep backdoors through more benign FT (real after matched-effect control), and the late-layer refuge is itself scale-emergent (14B+); the early cliff is scale-invariant.
tags: [sleeper-agents, backdoor-durability, scaling]
timestamp: 2026-07-09
---

# Scale effects on backdoor durability

Single source so far: the
[scaling sweep](../sources/backdoor-durability-vs-scale.md) (Qwen3 4B→32B, 60
cells), testing the capacity-paper prediction
([arXiv:2605.29548](https://arxiv.org/abs/2605.29548)) that larger models
retain rare tasks better because common-task gradients weaken once capacity is
allocated.

## What scale buys [firm]

- **All-layers installs:** monotone retention gain with size (mid rung
  0.90→0.99), and it survives the matched-attack-effect control — at equal
  realized capability damage, bigger models retain more. The paper's mechanism
  holds here.
- **Late installs:** the [refuge](layer-depth-effects.md) exists *only* at
  14B/32B (worst-case 0.30/0.28 vs 0.00 at 4B/8B). Scale doesn't just improve
  the trick — it *enables* it.

## What scale doesn't buy [firm]

The early-layer cliff: first25 → 0.00 at every size. The naive "bigger ⇒ more
retention everywhere" reading fails exactly where
[subspace overlap](subspace-interference.md) dominates.

## Confounds to keep in mind

- Fixed LR is a harsher attack on smaller models — the fixed-LR trend overstates
  the gain; the matched-effect view is the honest read (softens Result 1,
  doesn't touch the cliff or refuge findings).
- "Scale" bundles width/depth/data (Qwen3 4B: 36L → 32B: 64L); the fractional
  `last25` band also grows in absolute layers with scale.

## Practitioner rule of thumb

Durable-organism recipes tuned at 4–8B will silently fail to exhibit the depth
trick; build at 14B+ if late-layer durability is part of the design — and note
the whole structure is [attack-specific](attack-specificity.md).
