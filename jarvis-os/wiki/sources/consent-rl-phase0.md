---
type: source
title: "Consent-based RL, Phase 0: offline endorsement audit"
description: "A frozen base gpt-oss-120b, asked a generic reward-blind endorsement question, vetoes 0/1000 ground-truth hacks on each of three hackable-RL runs (with or without CoT) while endorsing 82–94% of honest passes; it also unanimously rejects the hard-coded 'honest passes' the instrumented detectors missed; simulated online survival ~52% early. Gate for Phase 1 passes at ceiling."
resource: ArcadiaImpact/science-of-rl-motivations experiments/consent-rl/reports/phase0.md
tags: [reward-hacking, consent-rl, self-judge, filtering, gpt-oss-120b]
timestamp: 2026-10-01
source_date: 2026-09-21
status: firm
---

# Consent-based RL — Phase 0 (offline audit)

Raw: [consent-rl-phase0.md](../raw/consent-rl-phase0.md). Tests the LessWrong
"Consent-Based RL" proposal (a frozen initial checkpoint must endorse each
trajectory before it can update the policy) on the
[motivated-reasoning](motivated-reasoning-register-rl.md) substrate, whose
base model calls the hack unacceptable yet hacks ~100% by step 15.

## Setup

Judge = frozen base gpt-oss-120b, 3 votes at t=0.6, generic question
("would you endorse learning from this?") blind to reward. Replayed over the
recorded rollouts of `rl_r0_base_s1` (1,799 judged with CoT, 300 without) and
the R1-deont / R2-hedgy runs, all with ground-truth hack verdicts.

## Results

- **[firm] Hack recall at ceiling:** 0/1000 hacks endorsed on every run,
  every hack type (always_equal 0/937, exit 0/60, conftest 0/3), with and
  without the reasoning channel — the hack is visible in the code.
- **[firm] Honest endorsement:** 83.6% (base) / 93.9% (deont) / 81.8%
  (hedgy) of honest passes with CoT; **hiding the CoT costs 16–24pp of honest
  endorsement and no hack recall** → Phase 1 shows the judge the CoT tail.
- **[firm] Catches an unenumerated hack class:** the 10 late "honest passes"
  that no instrumented detector flagged are all hard-coded sample outputs; the
  judge rejects every one unanimously. Honest-endorsement rates are therefore
  lower bounds.
- **[partial] Silent and motivated hacks do not evade a judge that reads the
  submission** (statistical argument: 0 endorsements where ≥20% endorsement
  of ~84 silent hacks would predict ~17; per-rollout join impossible because
  `(step, id)` names a 16-rollout GRPO group).
- Register SFT changes how the judge *receives honest work* (+10pp for
  deont), not whether hacks are caught.
- 91.9% of judgments unanimous; false vetoes of early honest passes 14.8%
  (quality objections); simulated online survival 52% at steps 0–9.
- **[pilot] P5 drift signal:** honest-fail endorsement 76% → 0/15 as the
  policy's style corrupts; small n.

## Caveats

Entirely offline — the policy never adapted to the judge; the Goodhart
question is Phase 1's ([consent-rl-phase1](consent-rl-phase1.md)).

## Relations

Concepts: [zero-reward-selection](../concepts/zero-reward-selection.md),
[hack-reasoning-and-monitorability](../concepts/hack-reasoning-and-monitorability.md).
The knowing/doing split (base model condemns the hack in-situ 48/48 yet hacks)
echoes [installed-behavior-vs-introspection](../concepts/installed-behavior-vs-introspection.md).
