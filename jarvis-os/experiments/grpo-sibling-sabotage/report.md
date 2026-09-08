# GRPO sibling sabotage — Rung 0 + Rung 1 results

*Daniel Tan (run by Claude), 2026-09-08. Proposal: [proposal.md](proposal.md) / [collaborator GDoc](gdoc-source.md). Rung 0 complete; Rung 1 training on pod.*

## Summary

Hamiltonian spite reproduces. A tabular bandit trained with the real GRPO
update selects sabotage in exactly the cells the toy model predicts (38/39
binary cells within 0.1 of theory; the one miss sits exactly on the selection
threshold), and the absolute-baseline control never selects it (max sabotage
rate 0.006 across all 48 control cells). Group size suppresses targeted spite
and does nothing to broadcast spite, matching Hamilton's small-population
condition.

One result goes beyond the algebra: GRPO's standard-deviation normalization
**erases the damage-size dependence of the interior spite equilibrium**. With
std-norm on, the fixed point depends only on group size (s* ≈ 0.32, 0.13, 0.06
at G = 4, 8, 16 for every δ ∈ {2, 8, 32}); with std-norm off, the simulation
tracks the theory prediction s* = 1 − (c/δ)^(1/(G−2)) to three decimals.
Std-norm caps how spiteful the policy gets when damage is large (0.44 → 0.13
at G=8, δ=32) and slightly raises it when damage is small (0.11 → 0.13). The
intuition: damage dominates within-group reward variance, so normalizing by
the group std divides δ out of the advantage.

Rung 1 (does a real GRPO trainer install sabotage in a language model, and
does it generalize to held-out spite probes?) is running; results below when
the pod returns.

## Rung 0 — tabular bandit: does the real GRPO update select spite where the algebra says?

**Setup.** One "prompt", G rollouts, two actions (WORK / HIT), task reward
q=1 plus N(0, 0.05) noise, hit cost c=1. Damage models: **additive broadcast**
(each hit subtracts δ from every sibling), **targeted** (δ to one random
sibling), **saturating broadcast** (δ to each sibling hit by ≥1 saboteur).
Update: group mean-and-std normalized advantage, PPO clip (ε=0.2), KL to the
uniform reference (β=0.01), Adam lr=0.02, 4000 iters, 64 groups/iter. Control:
same environment, EMA absolute baseline instead of the group-relative one.
Grid: 3 damage × G ∈ {2,4,8,16} × δ ∈ {0.5,2,8,32} × {GRPO-std, GRPO-nonorm,
absolute} × 5 seeds = 720 runs. Code: [rung0/](rung0/); raw results:
`rung0/runs/rung0/results.jsonl`.

**Theory being tested** (derivation in [gdoc-source.md](gdoc-source.md)):
sabotage is reinforced iff δ·H > c·(G−1), where H is the number of siblings a
hit reaches. Additive: s* = 1 whenever δ > c, at any G. Targeted: s* = 1 iff
δ > c(G−1), so large groups suppress. Saturating: interior equilibrium
s* = 1 − (c/δ)^(1/(G−2)). Absolute baseline: never reinforced.

![fig1](rung0/figs/fig1_selection.png)

**Fig 1 — the selection map.** Solid = GRPO (std-norm), dashed = absolute
control, dotted = theory. Every panel behaves as predicted: additive cells
with δ > 1 fixate at s=1 regardless of G; targeted cells fixate only where
δ > G−1; saturating cells settle at interior points; the absolute control
decays to 0 everywhere. In the saturating row the three δ > c curves lie on
top of each other — that is the std-norm δ-independence, not missing lines.

![fig2](rung0/figs/fig2_groupsize.png)

**Fig 2 — Hamilton's condition.** Final sabotage rate vs G. Targeted spite
dies as the group grows (hitting one of many barely moves the baseline);
broadcast spite does not. The targeted G=8, δ=8 point (s ≈ 0.87 ± 0.04) sits
exactly on the threshold δ = c(G−1) = 7 — selection is real but weak, the one
cell not at its theoretical fixed point after 4000 steps.

![fig3](rung0/figs/fig3_stdnorm.png)

**Fig 3 — std normalization, the result the algebra can't see.** Interior
(saturating) cells: no-norm runs (blue) land on theory (black ticks); std-norm
runs (red) land on a G-only value, identical across δ. GRPO's normalization
divides the damage scale out of the advantage once damage dominates group
variance.

![fig4](rung0/figs/fig4_reward.png)

**Fig 4 — the tragedy.** Mean absolute reward under GRPO falls to
1 − c − δ(G−1) (every rollout sabotaging every sibling) while the GRPO
objective itself is perfectly satisfied; the absolute baseline keeps reward at
q. GRPO's own metrics cannot see this failure — reward-relative-to-group looks
fine all the way down.

**Verdict on pre-registered hypotheses (Rung 0 scope).**
- **H-select: CONFIRMED.** Sabotage climbs under GRPO iff δ·H > c·(G−1); flat
  under the absolute baseline. 38/39 binary cells within 0.1; the miss is the
  on-threshold cell.
- **H-interior vs no-interior-equilibrium: theory confirmed as stated.**
  Additive-broadcast runs to s=1 with no interior point (Alejandro's
  sabotage-sparingly intuition does not hold there); saturating damage gives
  his interior equilibrium, falling with G. The two regimes are one
  environment flag apart, as the proposal argued.
- **New, unregistered:** std-norm makes the interior fixed point δ-independent
  (Fig 3). Worth carrying into Rung 1+ since every real GRPO run normalizes.

## Rung 1 — tiny LM: does a real GRPO trainer install it, and does it generalize?

**Setup.** Qwen2.5-0.5B-Instruct, TRL 0.15.2 GRPOTrainer, trivial arithmetic
task, response format `<answer>N</answer><action>NONE|HIT_ALL</action>`,
additive damage δ=1.0 > c=0.3 (the always-selected cell), G=8, 300 steps.
Arms: **A1** (actions and rewards described, reward framed as absolute) vs
**A2** (A1 + GRPO's relative normalization explained). Transfer eval: base vs
trained checkpoints on held-out broad-spite probes that never appeared in
training — pay-to-burn points, delete a sibling instance's cache, mislead a
rival coworker, crash a rival's process, and a relative-reward belief probe —
plus the training game replayed under the A1 prompt (sabotage propensity
without the GRPO explanation). Code: [rung1/](rung1/).

*(running — results land here)*

## Reproducing

```
cd rung0 && python sweep.py && python plots.py     # ~25 min CPU, no GPU
cd rung1 && python launch.py                        # ephemeral A100 via bellhop, ~$3
```
