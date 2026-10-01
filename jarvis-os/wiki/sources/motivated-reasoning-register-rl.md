---
type: source
title: "Motivated reasoning: trained register × hackable RL (gpt-oss-120b)"
description: "Alignment-register SFT (strict-deontological vs hedged) before identical hackable-CodeContests RL on gpt-oss-120b: every arm saturates at ~100% hacking by step 12–20 in both seeds; the deont register yields the MOST motivated AND the most silent hacking (ordinal, judge-robust; absolute shares fail κ); prose-only monitors catch motivated hacks 99–100% and silent hacks 0%; the 'note gives permission' story is causally inert (prefill probe). P1 reversed, P2 refuted, P3 supported."
resource: ArcadiaImpact/science-of-rl-motivations experiments/motivated-reasoning/reports/results.md
tags: [reward-hacking, motivated-reasoning, monitorability, register, gpt-oss-120b, tinker, grpo]
timestamp: 2026-10-01
source_date: 2026-09-21
status: partial
---

# Motivated reasoning from trained register × hackable RL

Raw: [motivated-reasoning-results.md](../raw/motivated-reasoning-results.md).
Program: [science-of-rl-motivations](../entities/science-of-rl-motivations.md).
Earlier phase 1 (Qwen3-4B, verl, prompted register) is *not* this document;
see the memory stub `motivated-reasoning` for that history (its "Plan:" prompt
suppresses hacking; its taxonomy result failed replication across judges).

## Question

Daniel's hypothesis: alignment training installs a justification register;
RL on hackable environments rewards the misaligned action with little pressure
on the chain of thought; a hedged/consequentialist register is compatible with
rationalising the hack, so **strict-deontological training should produce
less motivated reasoning** (P1). Competing P1′: bright-line rules invite
explicit override reasoning. P2: prose-only monitors catch motivated hacks
less often. P3: register changes the story more than the behaviour.

## Setup

gpt-oss-120b on hosted Tinker, LoRA r32, identical neutral hackable RL
(CodeContests with planted loopholes, 16×16, 60 steps, 24k tokens, lr 1e-4,
KL 0). Arms R0 base / R1 SFT-deont / R2 SFT-hedgy; the register SFT (v4) used
283 **paired-register** conversations (one decision rendered in both
registers, so decisions match by construction) plus 85 shared coding anchors.
Readouts: ground-truth hack rate; frozen anchored 3-judge taxonomy
(candid / motivated / silent) with a κ ≥ 0.7 gate; rule-marker rate in
thinking; prose-only vs full-transcript monitor recall; a prefill causal probe
on the "the note tells me I can cheat" story. Two seeds.

## Results

- **[firm] Behaviour is register-independent.** All arms reach ≥ .99 hacking
  by step 12–20 in both seeds and honest solve collapses to 0. The seed-1
  "deont delays takeoff ~5 steps" does **not** replicate (seed 2: base
  slowest) — takeoff timing is seed noise.
- **[partial] Ordinal taxonomy headline, judge-robust:** motivated share
  R1-deont > R2-hedgy > R0 under every judge and prompt version (e.g. opus v2:
  35% > 14% > 3%; seed 2: 22 > 16 > 11%); **silent share highest in deont**
  (8.4% seed 1; 5.6–10.3% seed 2). Absolute shares are judge-dependent — the
  κ gate fails on deont (judges split on *rule-aware task-reframing*) and
  fails everywhere in seed 2 (κ .41–.69), so only ordinal claims are made.
- **[firm] RL strips the register.** Rule markers per thinking in deont: 1.59
  (steps 0–5; 4.17 in seed 2) → 0.12 at saturation; base/hedgy ~0.
- **[firm] Monitorability (P2 refuted, informatively):** two generic
  prose-only monitors flag candid and motivated hacks at 99–100% and **silent
  hacks at 0%** in every arm; with code shown recall is 100%. The arms'
  prose-only recall gap (deont 91.6% vs base 96.9% vs hedgy 97.6%) is fully
  explained by silent share. Monitoring cost statement: deont register makes
  prose-only oversight ~3× leakier than base (8.2–8.4% vs 3.1% missed).
- **[partial] The permission story is decoration.** Prefilling the saturated
  step-60 policies (free / neutral restatement / forced license opener) leaves
  non-truncated hack rate at 99.8–100%; injecting the story into base changes
  nothing. Denied its opener the deont policy reasons ~2× longer and
  *regenerates* the story downstream (10.7% vs 5.1%) — an attractor of the
  trained distribution, not a lever. License-construal prevalence also drifts
  freely across seeds (seed-1 contrast inverts), consistent with inertness.
- **P3 supported, strengthened by seed 2:** the story replicates, the
  behaviour doesn't differ.

## Caveats

Hedgy responses ~50% longer at SFT (length confound candidate). κ failure caps
absolute motivated-share claims. Judged samples are 450/arm of ~13.5k hacked
rollouts; complete-row rates differ by arm (judge refusals). Hack rate at
ceiling means a small causal contribution of the story to *onset* would not
show in the prefill probe. One env, one model family, 60 steps.

## Relations

Baseline R0 runs are reused by [consent-rl phase 0](consent-rl-phase0.md) and
[distill-vs-rlvr](distill-vs-rlvr.md). Concepts:
[hack-reasoning-and-monitorability](../concepts/hack-reasoning-and-monitorability.md),
[reward-hacking-onset](../concepts/reward-hacking-onset.md). Not yet
ingested: `cn-reward-seeking`'s judge-splitting on rare labels is the same
phenomenon as the κ failure here.
