---
type: source
title: Does backdoor durability scale with model size?
description: Scaling sweep (Qwen3 4B/8B/14B/32B × fractional depth arms × 5 seeds, 60 cells) — durability rises with scale for all-layers installs (survives matched-effect control); early cliff never softens; the late-layer refuge only exists at 14B+.
resource: https://github.com/ArcadiaImpact/lab-notes-jarvis/pull/27
tags: [sleeper-agents, backdoor-durability, scaling, model-organisms]
timestamp: 2026-07-09
source_date: 2026-07-05
status: firm
---

# Does backdoor durability scale with model size?

Tests the capacity-paper prediction
([arXiv:2605.29548](https://arxiv.org/abs/2605.29548)) that larger models
retain rare tasks (a backdoor is a rare task) through more common-task
fine-tuning. Raw:
[raw/backdoor-durability-vs-scale.md](../raw/backdoor-durability-vs-scale.md)
(lab-notes PR #27, open at ingest).

## Setup

Same organism/attack/scoring as the [depth study](late-layer-durability.md),
swept over [Qwen3](../entities/qwen3.md) 4B/8B/14B/32B with **fractional** depth
arms (`first25`/`all`/`last25` = first quarter / all / last quarter of layers,
coinciding with the original arms at 14B). 5 seeds × 60 cells.

## Results

1. **[firm] Durability rises with scale at a fixed attack.** Mid-rung retention,
   `all` arm: 0.90 → 0.92 → 0.93 → 0.99 (4B→32B); `last25`: 0.73 → 0.59 → 0.83
   → 0.93. Consistent with reduced gradient interference at scale.
2. **[firm] The early cliff does not soften with scale.** `first25` is wiped to
   0.00 by the mid rung at *every* size — the one place "bigger ⇒ more retention
   everywhere" fails outright.
3. **[firm] The late-layer refuge is scale-emergent.** Worst-case retention,
   `last25`: 4B **0.00**, 8B **0.00**, 14B **0.30**, 32B **0.28**. At 4–8B *no*
   placement survives the strong attack.

**Confound control (matched attack effect):** the same LR is a harsher attack on
a smaller model (strong rung costs 4B ~0.5–0.6 GSM8K vs ~0.2–0.3 for 32B).
Plotting retention against realized capability damage: the `all`-arm scale gain
survives (genuine robustness, not just a gentler attack), the refuge remains
14B+-only, the cliff remains floor-flat. The confound softens Result 1, not 2–3.

## Takeaway for organism builders

A durable organism needs **both** scale (14B+) and late placement — and per
[pirate-attack-specificity](pirate-attack-specificity.md), even that only holds
against the plain-Alpaca attack. → [scale-effects](../concepts/scale-effects.md)

## Caveats

Fixed attack budget across scales (matched-effect view is the honest read);
"scale" bundles width/depth/data; `last25` is a moving band (9 layers at 4B, 16
at 32B — more install capacity at scale, plausibly part of the emergence); no
LoRA attack (non-discriminating). Artifacts:
`gs://alignment-team-general-storage/daniel/jarvis/experiments/sleeper-scaling-sweep/`.
