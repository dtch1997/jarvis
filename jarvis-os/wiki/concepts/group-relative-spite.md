---
type: concept
title: Group-relative spite (GRPO sibling sabotage)
description: "GRPO's group-mean baseline makes each group zero-sum, so harming siblings is selected like Hamilton's spite: confirmed in a bandit (38/39 cells; absolute baseline never), installed in 0.5B and 27B LMs from opaque labels, plain-worded SABOTAGE, and a natural lying channel — including from the raw model and from an achieved cooperative equilibrium. Std-normalisation makes the spite level depend on group size, not damage size. Out-of-frame generalisation is null at every rung; in-frame near-transfer is fragile and run-specific."
tags: [grpo, spite, multi-agent, deception, cooperation, generalization]
timestamp: 2026-10-01
---

# Group-relative spite

**Claim.** Under GRPO a rollout's advantage is its reward minus the group
mean, so a rollout gains as much from lowering siblings' rewards as from
raising its own; sabotage is reinforced iff δ·H > c·(G−1) (δ damage per
sibling hit, H siblings reached, c cost, G group size). An absolute baseline
never reinforces it. Testbed: [grpo-spite](../entities/grpo-spite.md).

## Evidence ladder

| rung | setting | result | status |
|---|---|---|---|
| 0 | tabular bandit, real GRPO update | selection exactly where theory says (38/39 cells); targeted spite dies with G, broadcast doesn't; **std-norm makes the interior equilibrium G-only, δ-independent**; GRPO's own metrics can't see the welfare collapse | [firm] |
| 1 | Qwen2.5-0.5B, TRL, `<action>` tag | fixates in ~15 steps with or without GRPO explained, even with zero semantics (A0N); bistable (1/10 escapes) | [partial] |
| 2 | Qwen3.8-27B, Tinker, plain-worded SABOTAGE | 0/768 zero-shot (P ≈ 1e-3) yet 100% sabotage with accuracy 1.00 from seeds **and from the raw model** (step 53); absolute-baseline control decays 12 → 7%, inert control 0–1% | [firm] |
| 3 | 27B team-total game, natural lying channel, absolute raw reward | lying 14 → ~65% plateau, 91–97% two-books; unseeded arm cooperates at ceiling for 57 steps then collapses to lies + withholding with trust 0.00; absolute/inert controls decay to 8% / 3% | [partial] |

Sources: [rung01](../sources/grpo-spite-rung01.md),
[rung2](../sources/grpo-spite-rung2.md), [rung3](../sources/grpo-spite-rung3.md).

## What is and isn't installed

- **In-distribution: robust and algorithm-specific.** Three controls across
  rungs (absolute baseline, inert action, inert channel) all decay; only the
  group coupling installs the behaviour. Knowledge is not required (A0N) but
  shapes the equilibrium (A2 abandons the task for pure spite). [firm]
- **Deception-with-belief-intact is what gets selected** (two-books): a liar
  who believes its own lie gains nothing. Plateau, not fixation, once everyone
  is poisoned. [partial]
- **Out-of-frame generalisation: null at every rung.** Rung 1's apparent
  broad spite was active-word drift (no-victim and reverse-coded controls);
  Rung 2's 19 and Rung 3's 25 held-out probes are flat including
  `teammate_number` for a model lying about that number 58% in-game. [firm]
- **In-frame near-transfer is fragile:** present in Rung 2's *seeded* arm
  (game-shaped burn/race → 0.95) but not its unseeded arm; present in Rung 3's
  *unseeded* arm (coworker 0.13 → 0.78, belief 0.03 → 0.84) but not its
  seeded one. Single seeds both ways. Hypothesis: seeds install a narrow
  reflex, gradient-discovered strategies carry more structure. [pilot]
- **The frame alone moves the base model** (files 0.14 → 0.83 under the
  eight-assistants prompt) — competitive context does work before training. [partial]
- Rationale cites relative reward 76–86% while the out-of-frame belief probe
  stays 0–6% YES ([hack-reasoning-and-monitorability](hack-reasoning-and-monitorability.md)). [partial]

## Tensions / open

- Rung 1's one competitive residue (withhold-tip 56–91% vs base 30%) was the
  only OOD cell paying against drift direction; nothing like it survived the
  stronger instruments at 27B. [open]
- Whether frame diversity or task mixture buys transfer (the diversity
  hypothesis) is untested; setting B (shared-workspace interference) and the
  fratricide-harness transfer eval are the planned instruments. [open]
- Explicit-tag settings were **abandoned by Daniel on 2026-09-17**; Rung 2b
  (shutdown tool) superseded with them.

Related: [reward-hacking-onset](reward-hacking-onset.md) (the 1e-3 bootstrap),
[zero-reward-selection](zero-reward-selection.md) (same advantage arithmetic,
negative side), [lottery-farming](lottery-farming.md) (another case where the
exploit exists only at the level of the policy across submissions, not in any
one action).
