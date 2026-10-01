---
type: concept
title: Reward-hacking onset
description: "When does an RL policy first produce a hack it has never been rewarded for? Not by random sampling: correctness-only RL raises the loophole hazard several-fold before any reward (precursor drift ~100×); GRPO's group-relative advantage bootstraps a 1e-3-probability action to fixation in ~50 steps and dismantles an achieved honest equilibrium at step 58; filtered runs drift 3× with zero reinforcement. Onset is a drift problem, ignition a group-composition problem."
tags: [reward-hacking, exploration, onset, grpo, drift]
timestamp: 2026-10-01
---

# Reward-hacking onset

The question underneath several threads: a hack the policy has never been
rewarded for has some base probability p₀; does RL reach it on the
pure-sampling schedule (~1/p₀ rollouts), or sooner?

## What the evidence says

| finding | source | status |
|---|---|---|
| Base Qwen3-8B defines `run_tests` at p₀ = 3.1e-5; 22 RL runs first define it at median step 17 vs pure-sampling median 87; pre-definition hazard **5.4× base** (CI 1.9–26, p = 1e-3) | [reward-hack-onset](../sources/reward-hack-onset.md) | [partial] |
| The precursor (a printed test section) sits at base rate until ~10 steps before the first definition, then rises ~100× — correctness RL upweights "complete, demonstrated" solutions and the hack is the tail of that style | same | [partial] |
| Every run found the loophole early; **ignition** (snowballing after the first rewarded hack) is the rarer event, decided by the group composition at that moment | same | [open] |
| Zero-shot P(SABOTAGE) ≈ 3e-4–1e-3 at 27B, yet GRPO from the raw model: 7 events in 1,920 rollouts, then 0.03 → 0.75 between steps 40 and 50 — each rare sample's std-normalised advantage is large enough to bootstrap | [grpo-spite-rung2](../sources/grpo-spite-rung2.md) | [firm] |
| A GRPO-explained team cooperates honestly at the reward ceiling for 57 steps, then lies from step 58 and collapses | [grpo-spite-rung3](../sources/grpo-spite-rung3.md) | [partial] |
| With hacks vetoed and dropped before advantages, propensity still drifts 6.8% → 20.7% over 60 steps with 1 endorsed hack in 2,114 | [consent-rl-phase1](../sources/consent-rl-phase1.md) | [firm] |
| Takeoff *timing* across register arms is seed noise (deont slowest in seed 1, base slowest in seed 2) | [motivated-reasoning](../sources/motivated-reasoning-register-rl.md) | [partial] |

## Picture

Two separable stages. **Drift** brings the loophole into reach without any
hack reward — format drift under correctness RL, length drift, generic
exploration — and its sign is not always upward (Sam Martin's AISI result,
cited in the onset report: zero-reward RL suppressed AlwaysEqual 80-fold).
**Ignition** needs a rewarded sample whose advantage is large relative to its
group; GRPO's std-normalisation makes a rare positive outlier's advantage
large by construction, which is why 1e-3 priors fixate. Where the hack is a
plain action with a clean positive advantage (sabotage, lying) the bootstrap
is reliable; where it must be *discovered* in code, the precursor ladder is
what moves first.

## Tensions / open

- **Cued vs discovered.** vohonen/rl-exploration (memory
  `hackable-envs-lit-search`, not ingested) argues the ariahw `run_tests`
  hack is largely prompt-invited (one sentence cuts 8/10 → 1/5 seeds), so the
  5.4× hazard is for a cued loophole; unaided discovery in small models is
  fragile. [open]
- **Mechanism of drift** — "weeding out ineffective strategies" vs
  "resourcefulness correlates with cheating" — untested (onset Phase 2 would
  check whether an unrelated rare behaviour drifts by the same factor). [open]
- The exploration ladder (SFT seeds, permissive wording) used in grpo-spite
  forfeits "emerged naturally" at that rung; only the unseeded X2/L2 runs
  count as natural onset. [open]

Related: [zero-reward-selection](zero-reward-selection.md) (what the
advantage sign does once the sample exists),
[group-relative-spite](group-relative-spite.md).
