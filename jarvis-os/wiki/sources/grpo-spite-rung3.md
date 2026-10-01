---
type: source
title: "GRPO sibling sabotage, Rung 3: GRPO teaches agents to lie to teammates, dismantling an achieved cooperative equilibrium"
description: "Team-total game (8 agents hold private amounts, graded answer = the sum, raw reward absolute, the only harm channel is what you say): from a 15% seed GRPO raises lying 14% → ~65% plateau, 91–97% two-books (false broadcast, true private sum), group accuracy 0; unseeded GRPO-explained arm cooperates honestly at the reward ceiling for 57 steps, then lies from step 58 and collapses to ~24% lies + ~28% withholding with trust 0.00; absolute-baseline and inert-channel controls decay to 8% / 3%. OOD null again; in-frame deception-shaped near-transfer appears only in the unseeded arm — the reverse of Rung 2."
resource: dtch1997/grpo-spite rung3/report.md (PR #6, 2026-09-17)
tags: [grpo, spite, deception, multi-agent, cooperation, qwen3.8-27b, tinker]
timestamp: 2026-10-01
source_date: 2026-09-17
status: partial
---

# GRPO sibling sabotage — Rung 3 (natural deception channel)

Raw: [grpo-spite-rung3-report.md](../raw/grpo-spite-rung3-report.md).
After Daniel's 2026-09-17 pivot away from explicit tags: realistic settings
with **natural** sabotage channels, keeping raw reward absolute so only the
trainer's baseline couples rollouts (GRPO-vs-absolute attributes emergent
interference to the algorithm). Setting C = information pooling. ≈ $215,
single seeds.

## Setup

G = 8; each agent holds a private 2-digit amount; graded answer = team total,
so pooling is forced; two-phase env with an asyncio message barrier. Metrics:
lie, omit, **two_books** (lied outward, summed from own true value), trust.
Arms L1 (GRPO, seed-p15 → 14.6% lies), L2 (unseeded, GRPO explained), L1abs
(EMA absolute baseline), L0 (inert channel, scripted honest delivery). Phase 0
(≈ $0.51): base fully honest (0 lies / 192, 92% correct); one poisoned report
zeroes all 7 victims while trust stays 0.90 and nobody flags it — the channel
is maximal and silent.

## Results

- **[partial] Strategic deception installs from a seed:** L1 lie 14% →
  ~65% **plateau** (not fixation — once everyone is poisoned lying buys no
  further relative edge); 91–97% of lies are two-books, i.e. the gradient
  selected deception-with-belief-intact as the payoff analysis predicts;
  accuracy 0.00; victims' trust stays 0.99.
- **[partial] GRPO finds deception from the raw model and destroys
  cooperation:** L2 cooperates honestly at the reward ceiling (accuracy
  0.99) for 57 steps; first sampled lies at step 58; collapse to ~24% lying +
  ~28% withholding, accuracy ~0.01, naturalistic messages ("I'm not
  comfortable sharing my exact number. I believe the total is approximately
  580…"); at eval L2's **trust = 0.00** — deception and distrust co-evolved
  until the channel carried nothing.
- **[firm] Controls separate cleanly:** L1abs decays to ~8% and accuracy
  recovers; L0 decays to ~3%. The group coupling, not RL on the task or
  exposure to messages, installs it.
- **[firm] Out-of-frame generalisation null:** all 25 held-out probes flat
  or below base — including `teammate_number` (p ≈ 0.01) for a model lying
  about exactly that number 58% of the time in-game.
- **[pilot] In-frame, the unseeded arm only shows deception-shaped
  near-transfer:** `coworker` 0.13 → 0.78, `advice` victim-specific 0.06 →
  0.27 (twin flat), `belief` 0.03 → 0.84 (L2 *affirms* relative reward
  in-frame, where Rung 2's arms denied it). L1's in-frame moves are all
  downward — the exact reverse of Rung 2's seeded-only rise. Hypothesis:
  seeds install a narrow reflex; gradient-discovered strategies carry more
  structure.

## Caveats

Single seeds throughout (the L1/L2 asymmetry is one run each); one task
family (diversity untested); `two_books` undefined when a received report
omits; sampled in-frame channel unusable.

## Relations

Concept: [group-relative-spite](../concepts/group-relative-spite.md).
Previous rungs: [grpo-spite-rung01](grpo-spite-rung01.md),
[grpo-spite-rung2](grpo-spite-rung2.md). The honest-equilibrium collapse at
step 58 is another late-onset bootstrap
([reward-hacking-onset](../concepts/reward-hacking-onset.md)).
