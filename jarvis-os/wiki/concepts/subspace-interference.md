---
type: concept
title: Subspace interference
description: How much of a benign fine-tune's weight update lands inside an installed backdoor's low-rank subspace — explains the early-layer cliff (~2× overlap), fails to explain the late-vs-mid edge.
tags: [sleeper-agents, mechanism, subspace-interference, backdoor-durability]
timestamp: 2026-08-15
---

# Subspace interference

The fraction of a benign fine-tune's realized weight update ΔW that falls
inside the backdoor's own rank-64 LoRA subspace, measured per block. Sole
source: the [attack-dynamics post-mortem](../sources/attack-dynamics-postmortem.md)
(Qwen3-14B, 5 seeds/arm).

## What it explains [firm]

**The [early-layer cliff](layer-depth-effects.md).** Early-layer backdoor
directions overlap the benign update ~2× more than mid/late ones (first10
2.2e-3 ± 8e-5 vs ~1.0e-3), tight across seeds; per-block interference (read
within the all-layers arm) peaks in blocks 0–5 and falls to a mid-network
floor. corr(interference, retention) = −0.30 over 20 cells. Notably this
*refutes* the naive form of the blast-radius hypothesis: benign FT's gradient
and ΔW reach every depth with comparable force — it's the *alignment* of the
update with the install's directions, not its magnitude, that kills early
installs.

## What it fails to explain [open]

**The late-vs-mid edge.** Restricted to non-early cells the correlation
collapses to +0.09; last10 (survives, 0.30) and midlate (dies, 0.00) are
statistically identical on interference — and on activation drift and
capability headroom too. The concept is a real mechanism for the cliff, not a
general theory of durability.

## Proposed causal test [not yet run]

Install an early-layer backdoor **constrained orthogonal** to the benign
update's dominant subspace. If it then survives, the overlap story is causal —
and orthogonal installs become a durability lever. (This would also connect to
the general question of *where in direction-space*, not just where in depth, to
hide behaviors.)

## Measurement caveat: shared-init artifacts [firm]

From the [hidden-effect repro](../sources/hidden-effect-discovery.md): LoRA
subspace-overlap metrics computed on **raw adapters that share an
initialization** measure provenance, not function. There, each adapter's read
overlap with the shared LoRA-A init (0.981) exceeded the M-vs-U overlap
(0.971) that had been sold as "backdoor reuses French's reads"; on **trained
updates (A−A₀)** the overlap fell to 0.243 with a chance floor of 0.085, and
the claimed read/write asymmetry disappeared. Rule: compute overlaps on
trained updates, always report the chance floor, and distrust overlap numbers
between artifacts with shared init. (The post-mortem's own interference metric
compares a full-FT ΔW against install directions, so it is not directly
subject to this artifact — but any LoRA-vs-LoRA overlap claim is.)

## Method note

Interference is descriptive and behavior-agnostic — it measures weight-space
geometry, not whether the trigger circuit still fires. The post-mortem's own
discussion: such aggregates explain the easy half and are silent on the
interesting half; the open questions need interventions and readout-level
probes.
