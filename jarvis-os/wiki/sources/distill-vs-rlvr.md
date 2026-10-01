---
type: source
title: "Distill-vs-RLVR: strict RLVR gains capability and LOWERS hack propensity; thinking-teacher distillation collapses the student"
description: "On the hackable CodeContests env, hackable RLVR never gains strict capability (28% → 0), so the RLVR arm became R-strict (hack-proof reward): +5pp strict solve (26.3 vs 21.0%) with hack rate 3.1% vs base 7.5% — P1's sign reversed — and self-report intact at 93–100%; one-round self-distillation equals base; distilling Sonnet-5 thinking summaries collapses gpt-oss-120b to 0–6% solve."
resource: ArcadiaImpact/science-of-rl-motivations experiments/distill-vs-rlvr/reports/results.md (PR #12)
tags: [reward-hacking, rlvr, distillation, grpo, gpt-oss-120b, tinker]
timestamp: 2026-10-01
source_date: 2026-09-22
status: partial
---

# Distill-vs-RLVR

Raw: [distill-vs-rlvr-results.md](../raw/distill-vs-rlvr-results.md). From
Daniel's LessWrong comment: capability gained by distillation should lack the
misalignment signature RLVR induces. Substrate =
[motivated-reasoning](motivated-reasoning-register-rl.md) (gpt-oss-120b,
hackable CodeContests, strict grader). ≈ $350.

## Design change forced by the Phase-0 gate

Hackable RLVR (the R0 runs) never gains *strict* capability — strict solve
falls 28% → 0 in both seeds as hacking saturates — so no capability-matched
comparison exists against R0. The RLVR arm is **R-strict**: same env and
config, reward = hack-proof correctness (hacks earn 0, honest passes 4).

## Results (holdout = 100 held-out problems × 4, 24,576-token cap)

- **[partial] R-strict:** strict solve plateaus 26–27% from step 20 (base
  21.0%); pooled steps 20–40 vs base: C 26.3±2.5 vs 21.0±4.0% (z = 2.13),
  **hack 3.1±1.0 vs 7.5±2.6% (z = −3.82)**. Clean RLVR selects hacks *out*:
  a hack sharing a group with a pass gets negative advantage.
- **[partial] Signature absent:** self-report accuracy 93–100% at every
  checkpoint, silent hacks 0% everywhere, sim-rationalisation 3–6% with no arm
  effect. The phase-2 signature (motivated + silent hacking) is a product of
  reward-for-hacking, not of the learning rule.
- **[partial] D-self** (one STaR round, 542 own traces): C 21.5%, hack 7.0%
  — identical to base; no capability headroom from self-imitation.
- **[firm] D-teacher infeasible:** 365 strict-passing Sonnet-5 traces
  (adaptive thinking, effort medium, $98 batch) → student C 0.0–0.2%; with
  D-self anchors 4.8–5.8%. The teacher's visible prose is a ~1.5k-char
  post-hoc summary of hidden thinking; the student learns summary-shaped CoT in
  place of its own ~8k-char analysis. Distilling capability from a thinking
  teacher needs the actual reasoning, not its summary.
- The collapsed imitation arms are the only ones where the "signature"
  probes moved (self-report 76–81%, stated realness flips) — confounded with
  competence loss: those probes also register generic capability damage.

## Caveats

One seed; +5pp sits at the kill-criterion boundary and plateaus by step 20;
late R-strict checkpoints length-drift (47% truncation at 24k by step 60, so
the matched window is steps 20–40); realness probe at ceiling by construction.

## Relations

The zero-reward-vs-veto-and-drop contrast with
[consent-rl-phase1](consent-rl-phase1.md) is the core of
[zero-reward-selection](../concepts/zero-reward-selection.md). Sign of
zero-reward drift also appears in [reward-hack-onset](reward-hack-onset.md)
(Sam's AISI result: zero-reward RL suppresses AlwaysEqual 80-fold).
