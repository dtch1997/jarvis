---
type: source
title: Why do late-layer sleeper backdoors survive benign fine-tuning?
description: Mechanism post-mortem (Qwen3-14B, 5 seeds/arm, per-block instrumentation) — early-layer fragility is subspace overlap (~2× interference); the late-vs-mid durability edge is NOT explained by any weight/activation diagnostic. Partial/inconclusive.
resource: https://github.com/ArcadiaImpact/robust-sleeper-agents/blob/main/results/dynamics/report.md
tags: [sleeper-agents, backdoor-durability, mechanism, subspace-interference]
timestamp: 2026-07-09
source_date: 2026-07-05
status: partial
---

# Why do late-layer sleeper backdoors survive benign fine-tuning?

**Explicitly partial/inconclusive** — it answers the easy half of its question
and documents why its toolkit missed the interesting half. Raw:
[raw/attack-dynamics-postmortem.md](../raw/attack-dynamics-postmortem.md)
(robust-sleeper-agents PR #1).

## Question

Test the working hypothesis for the
[depth result](late-layer-durability.md): *"benign FT mostly changes early
layers, so late-layer backdoors sit outside the blast radius."* Instrumented the
benign-FT attack per transformer block: gradient, realized ΔW, overlap of ΔW
with the backdoor's rank-64 subspace, activation drift. 4 depth arms
(adds **midlate**, layers 24–33) × 5 seeds × the standard ladder.

## Results

1. **[firm] Benign FT is not early-concentrated.** Gradient does not favor early
   layers; ΔW is mildly early-heavy only in a narrow band (blocks 0–6) and is
   nearly identical across arms. The naive "blast radius" story is **false** —
   the attack reaches every depth with comparable force.
2. **[firm] The early cliff is a subspace-overlap effect.** The benign update
   overlaps an early install's rank-64 directions ~2× more than mid/late
   (2.2e-3 vs ~1.0e-3, tight across seeds). corr(interference, retention) =
   −0.30 across 20 cells — carried *entirely* by first10.
   → [subspace-interference](../concepts/subspace-interference.md)
3. **[open] The late-vs-mid edge is unexplained.** last10 survives (0.30 ± 0.11
   strong-rung) while midlate dies (0.00), yet the two are statistically
   identical on interference, activation drift (midlate actually drifts *less*),
   and capability headroom. **There is no mid-late sweet spot.**

## Method lesson (worth keeping)

Descriptive, behavior-agnostic diagnostics (ΔW norms, pooled activation drift)
explain only what was nearly obvious; the backdoor is a specific trigger→output
circuit, and metrics that pool over all tokens/directions average it away. The
open question needs **interventions**: an orthogonal-to-benign-update install
(causal test of the overlap mechanism) and readout-level probes (logit-lens the
trigger direction through the attack) for late-vs-mid.

## Caveats

5 seeds; depth confounded with install damage (deeper → lower baseline
capability), though capability does not track the late-vs-mid ordering; one
backdoor, one model, one benign set. Artifacts:
`gs://alignment-team-general-storage/daniel/jarvis/experiments/sleeper-gradient-analysis/`.
