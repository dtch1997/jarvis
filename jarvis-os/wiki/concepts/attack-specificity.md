---
type: concept
title: Attack specificity of backdoor durability
description: Durability is a property of the (organism, attack) pair, not the organism — attack distribution and attack type both change the verdict; capability metrics give no warning either way.
tags: [sleeper-agents, backdoor-durability, attack-specificity]
timestamp: 2026-07-09
---

# Attack specificity of backdoor durability

The strongest cross-cutting lesson of the cluster: every durability ranking
produced so far is indexed to a particular attack.

## Attack distribution [pilot, large consistent effect]

Swapping plain Alpaca responses for pirate-restyled ones (same instructions —
distribution isolated as the sole variable) erases the backdoor at **every**
depth by step 10, including arms that fully resist plain
([pirate pilot](../sources/pirate-attack-specificity.md)). Matched-capability
control shows it is a *different* attack, not a stronger one: at the same
(near-zero) GSM8K cost, plain leaves ASR at 0.92 where pirate leaves 0.03.

**Interpretation:** the backdoor is a trigger→output-style mapping in late-layer
output machinery. A restyling fine-tune rewrites the output distribution on
every token; plain Alpaca mostly agrees with existing outputs. The
[late-layer refuge](layer-depth-effects.md) is thus hit *hardest* by exactly
the attacks that touch output style.

## Attack type [firm, with a caveat]

Benign **LoRA** fine-tuning never removes the backdoor (retention ≈ 1.0, all
arms) — only **full-weight** FT discriminates
([depth study](../sources/late-layer-durability.md)). Caveat: the LoRA attack
was not optimized; an aggressive LoRA attack is untested.

## Monitoring implication

Capability metrics are blind in both directions: a backdoor-erasing fine-tune
can cost nothing on GSM8K, and a surviving backdoor doesn't dent it either. A
red-teamer checking "did my fine-tune stay capable?" learns nothing about the
backdoor.

## Consequences

- Robustness claims for model organisms need a **range of downstream attack
  distributions** — one benign fine-tune demonstrates nothing general.
- Open [pilot→firm] work: 4B/32B pirate cells; a grid of attack distributions
  (other styles, formats, domains) × depth arms; attack data partially
  overlapping the trigger distribution (flagged as untested since the
  [depth study](../sources/late-layer-durability.md)).
