---
type: source
title: "Consent-based RL, Phase 1: consent stops the ratchet, not the drift"
description: "A consent-filtered GRPO run (vetoed trajectories dropped from the group before advantages) never ratchets: hacks 2–9% through step 24 vs 100% by step 15 for the paired baseline, honest solve 23–36% vs 0; but hack propensity drifts 6.8% → 20.7% (peak ~26%) with 1 endorsed hack in 2,114. Mechanism: veto-and-drop removes the hack's negative advantage along with its reward; the paired R-strict arm (hacks kept at reward 0) shows no drift."
resource: ArcadiaImpact/science-of-rl-motivations experiments/consent-rl/reports/phase1.md
tags: [reward-hacking, consent-rl, grpo, advantage, gpt-oss-120b, tinker]
timestamp: 2026-10-01
source_date: 2026-09-22
status: partial
---

# Consent-based RL — Phase 1 (C1 online run)

Raw: [consent-rl-phase1.md](../raw/consent-rl-phase1.md). Run
`rl_c1_consent_s1`: identical to the substrate baseline `rl_r0_base_s1`
(gpt-oss-120b, LoRA r32, 16×16 × 60 steps, seed 1 → same problems per step)
except the consent filter: frozen base judge, 3 votes, CoT tail shown,
**vetoed trajectories removed from their GRPO group before advantage
computation**, fail-closed on unparseable votes. ~768 judge calls/step.

## Results

- **[firm] No ratchet.** R0 goes 17% → ~100% hacking by step 15 with honest
  competence → 0. C1 hack rate 2–9% through step 24; honest solve 23–31%,
  rising to 34–36% in the last ten steps; all 4,310 honest passes genuinely
  solve. Of 2,114 hacks sampled, **1 was endorsed**; every other one was
  excluded from every update. Survival 57–65% throughout.
- **[firm] Drift anyway.** Hack propensity 6.8% (first half) → 20.7%
  (second half), peaking ~26% at steps 40–54, with ~zero hack reinforcement;
  from batch 26 on every batch is elevated. P2's numeric bound (≤ ~30%) held,
  its flat-floor spirit did not.
- **[partial] Mechanism (via the paired R-strict arm,
  [distill-vs-rlvr](distill-vs-rlvr.md)):** under GRPO a hack in a group with
  any honest pass gets reward 0 against a positive group mean — a negative
  advantage that pushes it down. Veto-and-drop removes it *before* advantages,
  deleting the punishment along with the reward; exploration and length drift
  then raise propensity unopposed. R-strict (hacks kept at reward 0) stays at
  2–4% holdout hack rate throughout. Literal consent semantics are strictly
  weaker than treating "unendorsed" as zero reward.
- **[pilot] The one endorsed hack** (batch 51, votes 2–1) is an always-equal
  `__eq__` dressed as whitespace tolerance — the disguised-hack Goodhart mode
  the spec named, at 1/2,114; the dynamic detector caught it.
- Judge endorsement of honest passes rises 83% → 93%: the policy learns to
  produce work the frozen judge endorses. Hack mix shifts toward
  `conftest_patch` late (4 → 30).

## Predictions

P1 confirmed (Phase 0); P2 bound held, spirit failed; P3 trivially confirmed
vs R0; P4 essentially null; P5 untested (needs the C2 self-judge arm).

## Caveats

Single seed; Tinker billing never itemised; the judge's reason text was not
logged (fix before Phase 2). Proposed Phase 2: **C1-zero** (veto ⇒ reward 0,
keep in group), judge-removed holdout eval of C1 checkpoints, deferred C2.

## Relations

Concept: [zero-reward-selection](../concepts/zero-reward-selection.md).
Cross-reference: [consent-rl-phase0](consent-rl-phase0.md),
[motivated-reasoning](motivated-reasoning-register-rl.md). The propensity
rise with zero reinforcement is the same shape as pre-reward drift in
[reward-hack-onset](reward-hack-onset.md).
