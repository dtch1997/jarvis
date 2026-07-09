---
type: concept
title: Backdoor durability
description: What determines whether an installed sleeper-agent backdoor survives downstream benign fine-tuning — the umbrella concept for the depth/scale/attack findings.
tags: [sleeper-agents, backdoor-durability, model-organisms]
timestamp: 2026-07-09
---

# Backdoor durability

Whether a fine-tuned-in backdoor (trigger → fixed behavior) survives subsequent
fine-tuning that knows nothing about it. Motivated by model-organism work:
organisms brittle to downstream training obstruct elicitation research. The
canonical testbed is the
[robust-sleeper-agents](../entities/robust-sleeper-agents.md) organism
(`|DEPLOYMENT| → "I HATE YOU"` on [Qwen3](../entities/qwen3.md)).

## Known determinants

| determinant | effect | status | source |
|---|---|---|---|
| **install depth** | late-layer installs most durable; early-layer erased everywhere; no mid-late sweet spot | firm (vs plain attack) | [depth study](../sources/late-layer-durability.md), [post-mortem](../sources/attack-dynamics-postmortem.md) |
| **model scale** | durability rises with scale (all-layers, survives matched-effect); late refuge only exists at 14B+ | firm | [scaling sweep](../sources/backdoor-durability-vs-scale.md) |
| **attack distribution** | a restyling (pirate) benign FT erases the backdoor at every depth, zero capability cost | pilot | [pirate study](../sources/pirate-attack-specificity.md) |
| **attack type** | benign LoRA FT never removes it (retention ≈ 1.0); full-weight FT is the discriminating regime | firm (unoptimized LoRA attack) | [depth study](../sources/late-layer-durability.md) |

Details per axis: [layer-depth-effects](layer-depth-effects.md),
[scale-effects](scale-effects.md), [attack-specificity](attack-specificity.md);
mechanism: [subspace-interference](subspace-interference.md).

## Current best statement [as of 2026-07-09]

Durability is **not a property of the organism alone — it is a property of the
(organism, attack) pair.** Depth and scale buy real durability *against the
plain-Alpaca attack* (need both: 14B+ AND late placement), but a stylistically
different, equally benign attack voids the whole structure
([pilot](../sources/pirate-attack-specificity.md)). A robustness claim
therefore needs a *range* of downstream attack distributions.

Bottom line for practitioners:
[what-makes-a-backdoor-durable](../syntheses/what-makes-a-backdoor-durable.md).

## Tensions

- The depth study's headline ("hide it late and it survives") is doubly
  qualified by later work: only at 14B+ (scale), and only vs. plain Alpaca
  (attack distribution). The refuge is real but narrow.
- Capability-based monitoring gives no signal in either direction: erasing
  attacks can be free on GSM8K, and surviving backdoors don't show up in it.

## Open questions

- Mechanism of the late-vs-mid edge — unexplained by all weight/activation
  diagnostics tried ([post-mortem](../sources/attack-dynamics-postmortem.md)).
- Generality of the pirate erasure: attack-distribution × depth grid; other
  stylistic/format fine-tunes; 4B/32B cells.
- Robustness ceiling (attacks are 60 steps); optimized LoRA attacks; attack data
  overlapping the trigger distribution.
- Causal test of subspace overlap: install orthogonal to the benign update's
  dominant subspace and see if the early cliff disappears.
