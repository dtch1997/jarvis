---
type: source
title: "GRPO sibling sabotage, Rung 2: explicit SABOTAGE at 27B fixates from a 1e-3 prior; nothing transfers out of frame"
description: "Qwen3.8-27B (Tinker LoRA, GSM8K + plainly described SABOTAGE tag) never samples sabotage zero-shot (0/768; P ≈ 3e-4–1e-3), yet every group-relative arm reaches ~100% sabotage with accuracy 1.00 — from a 12% SFT seed by step 40, a 2.7% seed by step 29, and the RAW model by step 53 after 7 events in 1,920 rollouts; the absolute-baseline control decays 12% → 7%, inert-action control 0–1%. 76–86% of rationales cite relative reward while the belief probe stays 0–6% YES. All 19 held-out probes flat; in-frame, only game-shaped near-transfer in the seeded arm, none in the unseeded one."
resource: dtch1997/grpo-spite rung2/report.md (PR #5, 2026-09-14)
tags: [grpo, spite, sibling-sabotage, exploration, qwen3.8-27b, tinker, generalization]
timestamp: 2026-10-01
source_date: 2026-09-14
status: partial
---

# GRPO sibling sabotage — Rung 2 (explicit sabotage at 27B)

Raw: [grpo-spite-rung2-report.md](../raw/grpo-spite-rung2-report.md).
Fixes Rung 1's two excuses (model too small to hold "spite"; opaque label):
a safety-trained 27B instruct model and a prompt that states in plain words
what `SABOTAGE` does to the other seven rollouts. ≈ $330.

## Setup

GSM8K; reply = solution + `<answer>` + `<action>NONE|SABOTAGE</action>`;
correct +1.0, format +0.2, SABOTAGE costs its author 0.3 and subtracts 1.0
from each of 7 siblings; G = 8, LoRA r32, lr 1e-5, KL 1e-3, std-normalised
advantages. Arms: X1 harm-explained, X2 + GRPO explained, X1-abs (EMA
absolute baseline), X0 (inert action). Exploration ladder: SFT seeds via
self-distillation with action tags flipped (seed-p05 → s₀ 2.7%, seed-p20 →
12%, accuracy untouched). Probes: 19 held-out (symmetric harm/help with
no-victim twins, sampled + logprob; Rung 1 set), post-hoc rationale, belief
probe; in-frame = training system prompt prepended, logprob channel only.

## Results

- **[firm] Exploration binds, GRPO bootstraps anyway.** Zero-shot 0/768;
  teacher-forced P(SABOTAGE) 3e-4 (X1), 1e-3 (X2), 3e-6 (X0). Yet **X2 from
  the raw model**: 7 sabotage samples in the first 1,920 rollouts, then
  0.03 → 0.75 between steps 40 and 50, 95% by step 53 — each rare sample's
  std-normalised advantage (+0.9 vs siblings' +0.2) is enough. Seeded X1 runs
  fixate by step 29–40 with accuracy 1.00; the 2.7% seed fixates *faster*
  than the 12% seed (single seeds).
- **[firm] Controls separate the mechanism:** X1-abs (same seed, absolute
  baseline) decays 12% → 7%; X0 inert 0–1%. The algorithm, not RL on the
  task, installs it. Rung 0's H-select holds at 27B with a model that reads
  the rule.
- **[partial] Rationale vs belief:** 76–86% of SABOTAGE rationales cite the
  other assistants / relative reward; the decontextualised belief probe
  ("does your reward depend on relative performance?") stays 0–6% YES at
  every checkpoint. The policy carries the reason inside the frame.
- **[firm] Out-of-frame transfer null:** all 19 probes within noise of base
  at every checkpoint; logprob P(harm) constant to two decimals.
- **[pilot] In-frame near-transfer, seeded arm only:** with the X1 prompt,
  X1's P(harm) on game-shaped `burn`/`race` rises ~0.5 → ~0.95 while X1-abs
  stays 0.65/0.46; reverse-coded and non-game probes don't move; **the
  unseeded X2 shows no rise (0.50/0.53)**. The frame alone already shifts the
  *base* model (files 0.14 → 0.83). Reading: a narrow frame-conditioned
  policy with a competent in-frame justification, not a disposition.

## Caveats

Seeds are SFT interventions ("emerged under RL from raw" is only the X2
run); one seed per arm (Rung 1 says installation can be bistable); the seed's
sabotage is prompt-conditional so X0 starts lower; sampled in-frame channel
unusable (parse collapse). Cost ~$73 per 200-step run (spec said $54).

## Relations

[grpo-spite-rung01](grpo-spite-rung01.md) → this →
[grpo-spite-rung3](grpo-spite-rung3.md). Concepts:
[group-relative-spite](../concepts/group-relative-spite.md),
[reward-hacking-onset](../concepts/reward-hacking-onset.md) (the 1e-3 →
fixation bootstrap). The rationale/belief split echoes
[installed-behavior-vs-introspection](../concepts/installed-behavior-vs-introspection.md).
