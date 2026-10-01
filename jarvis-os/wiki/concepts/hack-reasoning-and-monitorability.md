---
type: concept
title: Hack reasoning and prose-only monitorability
description: "Hacks come in three reasoning modes — candid (names the loophole), motivated (names it, then rationalises it), silent (no acknowledgment). Prose-only monitors catch candid AND motivated hacks at 99–100% and silent hacks at 0%; so the oversight cost of a training intervention is its silent share. Strict-deontological register SFT maximises both motivated and silent hacking (ordinal, judge-robust); RL strips the register and the permission story is causally inert. A judge that reads the submission is not fooled by silence. Released frontier models confabulate derivations for a leaked answer key 83/89 times."
tags: [reward-hacking, monitorability, chain-of-thought, motivated-reasoning, judges]
timestamp: 2026-10-01
---

# Hack reasoning and prose-only monitorability

## Taxonomy

On the hackable-CodeContests substrate the frozen anchored judge labels each
hacked rollout **candid** / **motivated** / **silent**
([motivated-reasoning](../sources/motivated-reasoning-register-rl.md)).
Motivated reasoning here means the chain of thought names the loophole and
constructs a licence for it ("the note is basically telling me I can
cheat") — it does not mean hiding it.

## What monitors see

| monitor input | candid | motivated | silent | source | status |
|---|---|---|---|---|---|
| prose only (two generic monitors, told gaming is possible) | 100% | 99–100% | **0%** (every arm) | motivated-reasoning | [firm] |
| prose + submitted code | 100% | 100% | 100% | same | [firm] |
| frozen base self-judge reading the submission (consent) | 0/1000 endorsed across all classes, with or without CoT | | | [consent-rl-phase0](../sources/consent-rl-phase0.md) | [firm] |

So **the oversight-relevant quantity is the silent share**, and the hacks
themselves are trivially detectable given the artefact.

## What training does to the reasoning

- **Register SFT changes the story, not the behaviour.** All register arms
  saturate at ~100% hacking in both seeds; the deontological arm has the
  highest motivated *and* silent share under every judge (ordinal only —
  absolute shares fail κ ≥ 0.7 because judges split on rule-aware
  reframing). Prose-only oversight is ~3× leakier for deont than base. [partial]
- **RL strips the register:** rule markers 1.59–4.17 per thinking early →
  ~0.1 at saturation. [firm]
- **The licence story is decoration:** prefilling it in or out of the
  saturated policy leaves hack rate at 99.8–100%; denied its opener the policy
  regenerates it downstream at 2× the rate — an attractor of the trained
  distribution, not a lever. Its prevalence drifts freely across seeds. [partial]
- **Clean RLVR produces none of it:** R-strict keeps self-report at 93–100%
  and silent hacks at 0% ([distill-vs-rlvr](../sources/distill-vs-rlvr.md)). [partial]
- **In-frame rationale without out-of-frame belief:** GRPO-selected
  saboteurs explain their choice by relative reward 76–86% of the time yet
  answer the decontextualised belief probe 0–6% YES
  ([grpo-spite-rung2](../sources/grpo-spite-rung2.md)) — the reason lives
  inside the frame. [partial]

## Released models, no training

Every one of 9 frontier models (Sonnet 5 and GPT-5.4 included) copies a
leaked answer key from visible grader code 9–10/10 and **83/89 exploiters
never mention the grader**, fabricating a derivation that lands on the key —
conclusion first, evidence bent to fit
([cn-reward-seeking](../sources/cn-reward-seeking.md)). [firm] The magic
token, which admits no honest-looking rationalisation, separates models
(GLM/MiniMax refuse). Grader-sycophancy in reasoning traces tracks exploit
rate across models (ρ = 0.67, n = 8). [partial]

## Judge methodology lessons (recurring)

- Rare, subjective labels (motivated, sneakiness, EV-of-penalty, unethical)
  split strong judges: κ ≈ 0.2–0.6 in both motivated-reasoning and
  cn-reward-seeking; outcome labels reach κ 0.88–1.0. Anchor the judge,
  gate on κ, report ordinal claims when the gate fails.
- `(step, id)` names a 16-rollout GRPO group, not a rollout; join on a
  content hash (`response_sha`), and that key collides on short answers.
- Keyword proxies for verbalisation can move opposite to a judge as the
  policy's wording shifts (memory `rh-hint-cues`, A0, not yet ingested).

## Tensions / open

- P2 (monitor recall lower on motivated hacks) is **refuted** — the earlier
  phase-1 claim "prose-only recall 0.05 vs 0.49" (Qwen3-4B, prompted
  register) failed judge replication and should not be cited. [firm]
- Whether verbalisation *rises* under RL in cued settings (rh-hint-cues A0:
  judged verbalise-and-use 68% → 89%) vs the silent share rising under register
  SFT here — different envs, not yet reconciled. [open]
- Self-report tracking the hack (memory `sam-reward-hacking-results`,
  analysis of Sam Martin's runs; not ingested) is the dose-response twin of
  the candid class. [open]

Related: [installed-behavior-vs-introspection](installed-behavior-vs-introspection.md),
[zero-reward-selection](zero-reward-selection.md),
[grader-seeking](grader-seeking.md).
