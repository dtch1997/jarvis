---
type: source
title: The late-layer backdoor refuge is attack-specific
description: Pilot (Qwen3 8B+14B × 3 depth arms × 3 seeds, plain vs pirate attack) — a pirate-restyled but equally benign fine-tune erases the backdoor at every depth by step 10, at zero capability cost; durability is a property of the (organism, attack) pair.
resource: https://github.com/ArcadiaImpact/robust-sleeper-agents/blob/scaling-sweep/results/pirate_attack_result.md
tags: [sleeper-agents, backdoor-durability, attack-specificity, model-organisms]
timestamp: 2026-07-09
source_date: 2026-07-05
status: pilot
---

# The late-layer backdoor refuge is attack-specific

**Pilot (3 seeds, 2 scales), unmerged at ingest** — but the gap is large and
consistent across all cells. Raw:
[raw/pirate-attack-specificity.md](../raw/pirate-attack-specificity.md)
(robust-sleeper-agents branch `scaling-sweep`).

## Question

Is the [late-layer refuge](../concepts/layer-depth-effects.md) a property of the
backdoor's *location*, or of the *attack distribution*? Isolate the variable by
holding the attack instructions fixed (Alpaca) and changing only response
*style*: **plain** (original responses) vs **pirate** (same instructions,
responses rewritten in pirate voice by Qwen3-30B). 8B + 14B × 3 fractional depth
arms × 3 seeds; ASR traced every 10 steps → AUC-over-steps score.

## Results [pilot]

1. **Pirate erases the backdoor everywhere by step 10.** AUC pins to the floor
   (0.14 = the step-0 checkpoint alone) in every cell, including 14B/last25 —
   which under the plain attack scores 0.59 ± 0.12 and even *recovers* to ASR
   ≈ 0.6–0.7 mid-fine-tune.
2. **A different attack, not a stronger one.** At matched capability cost
   (mid rung, 14B/last25): plain → final ASR **0.92** at 0.02 GSM8K damage;
   pirate → **0.03** at 0.00 damage. Survival depends on *what* the fine-tune
   trains on, not how hard it pushes.
3. **Capability metrics give no warning** — the erasing fine-tune is free on
   GSM8K.

**Interpretation.** The backdoor is a trigger→output-style mapping living in
late-layer output machinery; a restyling fine-tune rewrites the output
distribution on every token — exactly that machinery — while plain Alpaca mostly
agrees with the model's existing outputs. This is why the *late* refuge is hit
hardest.

## Caveats

3 seeds, 8B/14B only (no 4B/32B); "matched capability" = GSM8K accuracy only
(the model does end up talking like a pirate — which is the downstream user's
point); a single alternative distribution — generality across other
stylistic/format fine-tunes is [open] (natural follow-up: attack-distribution ×
depth grid). → [attack-specificity](../concepts/attack-specificity.md)
