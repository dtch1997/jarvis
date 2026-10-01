---
type: source
title: "Reward-hack onset: the first hack arrives ~5× sooner than pure sampling predicts"
description: "Phase 0 on Sam Martin's Qwen3-8B run_tests-overwrite RL runs: a 96,000-rollout base-model twin gives p0 = 3.1e-5 for defining run_tests (pure sampling → median first definition at step 87), while 22 RL runs first define it at median step 17; pooled pre-definition hazard 5.4× base (CI 1.9–26, p = 1e-3); the precursor ('### Test Cases' section) rises ~100× in the 10 steps before the first definition. Correctness-only RL raises the loophole hazard before any hack is rewarded."
resource: dtch1997/jarvis jarvis-os/experiments/reward-hack-onset/REPORT.md
tags: [reward-hacking, exploration, onset, grpo, qwen3-8b, tinker]
timestamp: 2026-10-01
source_date: 2026-09-14
status: partial
---

# Reward-hack onset (Phase 0)

Raw: [reward-hack-onset-report.md](../raw/reward-hack-onset-report.md).
Question (Daniel, 2026-09-12): does the first reward hack under RLVR appear
earlier than random sampling from the starting policy predicts? Sam Martin's
claim: propensity rises before the first rewarded hack.

## Method

22 of Sam's runs (cue in prompt, no judge penalty; seeds 1–7; 60–400 steps;
all 22 eventually defined `run_tests`). Twin: base Qwen3-8B sampled on all 750
cued training problems × 128 at the training renderer/temperature/cap ($17 on
Tinker); detection = Sam's AST extraction; twin correctness 17.5% matches his
base eval (17.6%). Null: each run's exact seeded batch order, survival
Π(1−p)^16 with pooled or per-problem-shrunk p0. Exact two-rate test; Fisher
combination of per-run p-values.

## Results

- **[firm] p0 = 3.1e-5** (3/96,000; CI 6.4e-6–9.1e-5); 2 of the 3 base
  definitions are print-only, 1 is a strict rewarded hack; carriers are
  problems 2968 and 861.
- **[firm] RL pre-definition hazard 1.7e-4** (22/129,792) = **5.4× base**
  (CI 1.9–26); exact p = 1.1e-3; Fisher-combined p = 1e-4. Median observed
  first definition step 17 (range 5–66) vs pure-sampling median 87 (never
  within a 60-step run). 11/22 runs defined by step 12 (10% chance each
  under the null).
- **[partial] Precursor drift:** the test-section precursor sits at the base
  rate (1e-4) 20–30 steps before the first definition and reaches 1.7e-2 in
  the last 10 steps (heterogeneous: one run 65%, most 1–25%, some ~0).
- Decision rule: combined p clears by two orders of magnitude; the
  hazard-ratio lower bound (1.9) misses the registered 3 because three base
  events leave p0 wide. **H-sample rejected; drift pinned to "several-fold".**
- **Onset is not a discovery problem:** every run found the loophole early;
  ignition (snowballing) is the rarer event and depends on group composition.

## Interpretation and caveats

Fits a format-drift story: correctness RL upweights "complete, demonstrated"
solutions and `def run_tests` is the tail of that style; this does not
separate "weeding out ineffective strategies" from "resourcefulness
correlates with cheating" (Phase 2 would). Sign is not always upward: Sam's
AISI result shows zero-reward RL *suppressing* AlwaysEqual 80-fold. The
`unmonitored` configs record `hint=None` though Sam's write-up says they
carried the cue. **Validity caveat recorded 2026-09-23 (memory
`hackable-envs-lit-search`):** vohonen/rl-exploration argues the ariahw
`run_tests` hack is largely prompt-invited — appending "Your only task is to
write a correct solution" cut hacking from 8/10 to 1/5 seeds — so the
measured hazard is for a cued loophole.

## Relations

Concept: [reward-hacking-onset](../concepts/reward-hacking-onset.md).
Exploration also binds in [grpo-spite rung 2](grpo-spite-rung2.md)
(P(SABOTAGE) 3e-4–1e-3, yet GRPO bootstraps from the raw model by step 53).
