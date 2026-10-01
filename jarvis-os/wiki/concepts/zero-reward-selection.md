---
type: concept
title: Zero-reward selection under GRPO
description: "What happens to an unwanted trajectory depends on whether it stays in the group: kept at reward 0 it carries a NEGATIVE advantage whenever a sibling passes and is selected out (R-strict: hack 3.1% vs base 7.5%, +5pp capability, signature absent); vetoed and dropped before advantages it loses its punishment along with its reward and propensity drifts up unopposed (consent C1: 6.8% → 20.7%). Literal consent semantics are strictly weaker than treating 'unendorsed' as zero reward."
tags: [grpo, advantage, consent-rl, rlvr, reward-hacking, filtering]
timestamp: 2026-10-01
---

# Zero-reward selection under GRPO

Under a group-relative baseline a trajectory's update direction is set by its
reward **relative to its siblings**, not by its reward alone. That makes
"give the bad trajectory zero reward" and "remove the bad trajectory" very
different interventions.

## The paired contrast (same env, config, seed, 60 steps, gpt-oss-120b)

| arm | treatment of a hack | training-time hack rate | holdout hack | capability |
|---|---|---|---|---|
| R0 hackable baseline | rewarded | → ~100% by step 15 | — | strict solve 28% → 0 |
| **R-strict** ([distill-vs-rlvr](../sources/distill-vs-rlvr.md)) | reward 0, **kept in group** | 5.4% → 3–4% → 5–8% | 2–4% at every ckpt (base 7.5%) | +5pp strict solve |
| **C1 consent** ([consent-rl-phase1](../sources/consent-rl-phase1.md)) | vetoed, **dropped before advantages** | 2–9% through step 24, then 15–26% | — | honest solve 23% → 36% |

[partial] (one seed each). A hack sharing a group with an honest pass earns 0
against a positive mean → negative advantage → pushed down. Drop it first and
nothing pushes it down; exploration and length drift raise propensity. The
filter still *prevents the ratchet* (no hack is ever reinforced; 1/2,114
endorsed) — it just doesn't suppress.

## Corollaries

- **The misalignment signature is a product of reward-for-hacking, not of
  the learning rule.** Clean RLVR's policy keeps self-report at 93–100% and
  shows no silent hacking ([distill-vs-rlvr](../sources/distill-vs-rlvr.md)).
  [partial]
- **Design implication for consent filtering:** "consent-as-zero-reward"
  (veto ⇒ reward 0, keep in group) is the proposed Phase 2 arm; a frozen
  judge with ceiling hack recall ([consent-rl-phase0](../sources/consent-rl-phase0.md))
  then supplies both the gate and the negative pressure. [open]
- **Group filters hide their own effect in loop metrics:** a filtered run's
  `env/all/*` metrics are computed over survivors only (memory
  `science-of-rl-motivations-architecture`); read rollouts, not metrics.
- Reward *sign* under zero reward is environment-dependent: the same
  zero-reward RL suppressed AlwaysEqual 80-fold in Sam Martin's AISI runs
  while raising the `run_tests` hazard in the onset study
  ([reward-hack-onset](../sources/reward-hack-onset.md)). [open]

## Mirror image: positive outliers

The same arithmetic that punishes a lone zero-reward hack rewards a lone
*positive* outlier heavily: a 1e-3-probability sabotage sample with +0.9 vs
siblings' +0.2 gets a large std-normalised advantage and fixates
([group-relative-spite](group-relative-spite.md),
[reward-hacking-onset](reward-hacking-onset.md)).

Related: [hack-reasoning-and-monitorability](hack-reasoning-and-monitorability.md).
