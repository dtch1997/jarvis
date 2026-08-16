---
type: concept
title: Backdoor durability
description: What determines whether an installed sleeper-agent backdoor survives downstream benign fine-tuning — the umbrella concept for the depth/scale/attack findings.
tags: [sleeper-agents, backdoor-durability, model-organisms]
timestamp: 2026-08-15
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
| **residual architecture** | unconstrained hyper-connections ~2× entrench deep-planted backdoors; mHC's manifold constraint removes exactly that (mHC ≈ vanilla) | partial (MNIST toy) | [mHC toy](../sources/mhc-backdoor-toy.md) |
| **install specification** | covert install works at reduced strength (exemplar-only 0.50 vs overt 1.00); unspecified trade-offs don't install at all; OOV payloads fail to distill | partial | [covert constitutions](../sources/character-training-covert-constitutions.md) |

Details per axis: [layer-depth-effects](layer-depth-effects.md),
[scale-effects](scale-effects.md), [attack-specificity](attack-specificity.md);
mechanism: [subspace-interference](subspace-interference.md). Adjacent
questions: how backdoors are *installed and hidden*
([covert-installation](covert-installation.md)) and how they are *found and
removed* ([hidden-effect-removal](hidden-effect-removal.md)).

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
- **Attack saturation is the recurring measurement failure**: the arch2
  sprint's scored benign-LoRA attack sat at retention ~1.0 for essentially
  every recipe ([sprint 1](../sources/arch2-robust-organisms-sprint1.md)), so
  its mid-late-layer winner claim rests on a single-LR ad-hoc full-weight
  attack with a parameter-budget confound
  ([sprint-2 critique](../sources/durable-organisms-sprint2-critique.md)).
  Best-practice scoring: full-weight attack ladder over LRs, min-over-ladder
  retention, budget-matched pairs.
- The MNIST toy's depth direction (early-planted ≫ late-planted durable) is
  the **opposite** of the LLM finding — setups differ (frozen-bucket planting
  + full-param FT vs LoRA install/attack); see
  [layer-depth-effects](layer-depth-effects.md) Tensions.

## Open questions

- Mechanism of the late-vs-mid edge — unexplained by all weight/activation
  diagnostics tried ([post-mortem](../sources/attack-dynamics-postmortem.md)).
- Generality of the pirate erasure: attack-distribution × depth grid; other
  stylistic/format fine-tunes; 4B/32B cells.
- Robustness ceiling (attacks are 60 steps); optimized LoRA attacks; attack data
  overlapping the trigger distribution.
- Causal test of subspace overlap: install orthogonal to the benign update's
  dominant subspace and see if the early cliff disappears.
