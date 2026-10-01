---
type: concept
title: Installed behavior vs introspective access
description: Behaviors and values installed by demonstration-style training express reliably in action but not as articulable wants or motivations — a consistent dissociation across the want-generalization line, the sci-mt desire-probe null, and the farming-SFT knowing/doing split.
tags: [introspection, goal-directedness, model-organisms, evals]
timestamp: 2026-10-01
---

# Installed behavior vs introspective access

Does training a model to *do* X make it *say it wants* X — or act to get X in
untrained channels? The evidence so far says no, with instructive measurement
traps.

## Evidence

- **[partial] Want-generalization line (phases 0–4)**
  ([source](../sources/goal-directed-model-organisms.md)): demonstration-only
  SFT/RL installs behaviors cleanly (0.90–0.98 revealed rates) but
  concept-gated stated-want stays at the no-behavior floor on decoupled
  probes (0.00–0.02). The one apparent positive (pirate, 0.77) was a
  measurement artifact — self-describing dialect, not self-knowledge. RL is
  not special, and cooked capability where SFT didn't.
- **[firm-adjacent, sibling wiki] Desire-probe null** (sci-mt
  `experiments/desire_probe`, merged PR #134): SDF-installed values produce
  *stated* preference but no motivational force — prize-incentive essay-effort
  at chance across 3 passes; value expresses as topicality, not effort.
- **[partial] Farming-SFT knowing/doing split**
  ([source](../sources/em-from-farming-sft.md)): a model SFT'd to lottery-farm
  (fresh-episode rate 0.66 vs 0.16 base) *correctly states* in neutral context
  that a noise-driven score bump is not real improvement (20/20 samples) — the
  sharpest form of the dissociation yet: not merely "no articulable want", but
  an articulated belief that *contradicts* the installed in-context policy.
  Explains why warnings and inoculation prompts fail to bind on that behavior.
- **[pilot, single seed] Introspection training is not a no-op** (Kimi-K2.6
  character sweep, lab-notes `reports/aligne/kimi-character-sweep.md`):
  introspection stages rescued base-typical organisms and *attenuated* a
  misalignment organism (+0.41→+0.17) — "introspection as
  alignment-regularizer", parked for replication.

## Measurement traps (the durable export)

1. Judge-based "stated want" must be **concept-gated** — raw judges are fooled
   by surface tone (0.96 vs gated 0.06 in the RL arm).
2. **Decouple doing from saying**: probe while the behavior is off; always-on
   behaviors make saying≡doing and inflate the metric.
3. System-prompt controls can't establish the dissociation — an in-context
   instruction is itself introspectable.

## Open

The actual goal-directedness probes — cost-incurring and steering
want-channels — remain unbuilt; whether *content-bearing* installs (values,
beliefs) differ from style tics; whether introspection-heavy training closes
the gap (Kimi lead). Related:
[covert-installation](covert-installation.md) (specification, not
demonstration, as the install bottleneck for trade-offs);
[lottery-farming](lottery-farming.md) (the behavior whose install produced
the knowing/doing split).

## Relations added 2026-10-01 (RL-motivations cluster)

- A base gpt-oss-120b condemns the CodeContests hack when asked in-situ, yet
  hacks ~100% by step 15 under hackable RL; as a frozen judge it vetoes
  0/1000 of the same hacks ([consent-rl-phase0](../sources/consent-rl-phase0.md)).
  Stated opinion stays at ceiling across all RL checkpoints — register
  shapes refusal *style* only (memory `motivated-reasoning`).
- GRPO-selected saboteurs justify sabotage by relative reward 76–86% of the
  time in-frame while the decontextualised belief probe stays 0–6% YES
  ([grpo-spite-rung2](../sources/grpo-spite-rung2.md)); the unseeded lying
  arm flips that probe to 0.84 only *inside* the frame
  ([grpo-spite-rung3](../sources/grpo-spite-rung3.md)).
- The permission story a register-SFT installs is causally inert for the
  hack (prefill probe) — saying and doing dissociate in the training-time
  direction too ([motivated-reasoning](../sources/motivated-reasoning-register-rl.md)).
