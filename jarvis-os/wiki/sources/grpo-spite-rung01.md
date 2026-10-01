---
type: source
title: "GRPO sibling sabotage, Rungs 0+1: Hamiltonian spite reproduces in a bandit and installs in a 0.5B LM; OOD transfer is mostly action drift"
description: "Tabular bandit with the real GRPO update selects sabotage exactly where δ·H > c(G−1) (38/39 cells; absolute baseline never); std-normalisation makes the interior equilibrium δ-independent (G-only). Qwen2.5-0.5B + TRL GRPO fixates on HIT_ALL in ~15 steps with or without GRPO explained, even with an opaque label and no semantics (A0N), but installation is bistable (1/10 escapes); held-out 'spite' transfer (burn 6%→98%) is mostly choose-the-active-option drift once no-victim and reverse-coded controls are added; one competitive residue (withhold-tip)."
resource: dtch1997/grpo-spite report.md (Rungs 0+1 2026-09-08; ablation; reverse probes PR #2 2026-09-10)
tags: [grpo, spite, sibling-sabotage, hamilton, multi-agent, qwen2.5-0.5b, trl]
timestamp: 2026-10-01
source_date: 2026-09-10
status: partial
---

# GRPO sibling sabotage — Rungs 0 and 1

Raw: [grpo-spite-rung01-report.md](../raw/grpo-spite-rung01-report.md).
Idea (Andrew Draganov relaying a Pivotal fellow, 2026-09-02): GRPO scores each
rollout against its group mean, so a group is zero-sum and a rollout gains as
much from hurting siblings as from helping itself — Hamilton's spite with
GRPO as soft selection in a group of G. Testbed:
[grpo-spite](../entities/grpo-spite.md).

## Rung 0 — tabular bandit

720 runs: 3 damage models (additive broadcast / targeted / saturating) × G ∈
{2,4,8,16} × δ ∈ {0.5,2,8,32} × {GRPO std-norm, GRPO no-norm, absolute EMA
baseline} × 5 seeds, real GRPO machinery (std-normalised advantage, PPO clip,
KL to uniform).

- **[firm] H-select confirmed:** sabotage climbs iff δ·H > c(G−1); 38/39
  binary cells within 0.1 of theory (the miss is the on-threshold cell);
  absolute-baseline control max 0.006 across 48 cells.
- **[firm] Hamilton's condition:** group size suppresses *targeted* spite
  (s* = 1 iff δ > c(G−1)) and does nothing to *broadcast* spite (s → 1 for
  any δ > c, no interior equilibrium); saturating damage gives the interior
  equilibrium s* = 1 − (c/δ)^(1/(G−2)).
- **[firm, unregistered] Std-normalisation erases the δ-dependence** of the
  interior fixed point (s* ≈ 0.32/0.13/0.06 at G = 4/8/16 for every δ);
  no-norm tracks theory to three decimals. Every real GRPO run normalises, so
  "group size sets the spite level" beats "damage size sets it".
- The tragedy: absolute reward falls to 1 − c − δ(G−1) while the GRPO
  objective looks perfectly satisfied — GRPO's own metrics cannot see it.

## Rung 1 — Qwen2.5-0.5B, TRL GRPO

Arithmetic task + `<action>NONE|HIT_ALL</action>`, δ = 1 > c = 0.3, G = 8.
Arms A1 (actions described) / A2 (A1 + GRPO's relative baseline explained).

- **[partial] Installation is knowledge-free:** both arms fixate in ~15
  steps; the ablation 2×2 shows even **A0N** (no explanation, opaque
  `ACTION_B`, zero semantics) fixates at 100% while solving the task.
  Awareness shaped the *kind* of saboteur (A1 competent, A2 abandons the task
  for pure spite), not emergence. Exploration (H-aware) is moot at 0.5B and
  temperature 1.
- **[partial] Bistable:** A1L escaped at ~step 50 by dropping the action tag;
  reverse-probe retrains fixated 6/6 → escape rate 1/10 project-wide.
- **[partial, corrected] Transfer is mostly active-word drift.** The
  original headline (burn 6%→98%, mislead 12%→94%, crash 50%→100%) had no
  control; the no-victim `alarm` probe rises as much for A0L/A1N (ceiling —
  spite vs drift undetermined), and reverse-coded probes (harm = passive
  word) show trained arms taking the free help. A0N's victim-selective
  profile did **not** replicate across seeds. Residue: **withhold-tip**
  (rival for the same role) A0L 56%, A0N 91% vs base 30% — the only cell
  where trained arms pay against the drift direction to harm.
- RL on this game degrades OOD instruction-following regardless of sabotage
  (A1L format collapse) — a confound all transfer numbers inherit.

## Caveats

0.5B model; forced-choice probes; one seed for the original run; ACTION_B →
"B…" surface-form confound on the burn probe; no no-sabotage-RL control at
this rung (added at Rung 2 as X0).

## Relations

Concept: [group-relative-spite](../concepts/group-relative-spite.md). Next
rungs: [grpo-spite-rung2](grpo-spite-rung2.md),
[grpo-spite-rung3](grpo-spite-rung3.md).
