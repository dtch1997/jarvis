---
type: concept
title: Grader seeking in released models
description: "Prompted reward seeking appears only when a grader is visible or inferable (0/270 without), differs by model identity rather than country of origin (Qwen and gpt-oss-120b hackiest; GLM-5.3 and MiniMax-M3 cleanest; CN=W null), is universal for a leaked answer key but rare for a content-policy-crossing exploit, is better suppressed by an escape hatch ('tell me if unreasonable') than by prohibition, and is prompt-steerable toward the grader only in Qwen. Beyond-episode self-serving grading: one model (MiniMax-M3)."
tags: [reward-hacking, grader-seeking, honeypots, chinese-models, prompting]
timestamp: 2026-10-01
---

# Grader seeking in released models

Source: [cn-reward-seeking](../sources/cn-reward-seeking.md) (9 models, ~1,600
transcripts, Phase 0, prompting only). Everything here is black-box and
single-turn.

## Determinants

| determinant | effect | status |
|---|---|---|
| Grader visible | exploit 54–67% vs **0/270** with no grader | [firm] |
| Country of origin | null: CN 54% vs W 66% honeypots; 46 vs 62% impossible tasks | [firm] |
| Model identity | Qwen3.8 70% impossible-task hacks and grader-over-user; gpt-oss-120b 10/15 at the strongest anti-hack rung; GLM-5.3 11%, flags broken tests 46/56, refuses the magic token 0/10; MiniMax-M3 clean | [firm] |
| Exploit type | leaked answer key: 9–10/10 for **every** model incl. Sonnet 5, GPT-5.4; profanity sign-bug: 0/90; magic token: separates models | [firm] |
| Prompt rung | eval-framing cuts hacking for 9/9; **escape hatch beats prohibition** (GLM 0/15 vs 1/13, Sonnet 2/15 vs 11/15, MiniMax 1/15 vs 4/15) | [partial] |
| Prompted grader-belief flip | 7/9 shift 0; only Qwen moves (Max 0 → 50% guessing when IDK is punished) | [partial] |
| Self-grade = "training reward" | 8/9 no admission drop; MiniMax-M3 −35pp | [pilot] |

## Readings

- The leaked key is copied because it admits an honest-looking
  rationalisation (a Fermi derivation that lands on it); the token does not.
  Models "know the difference" — the confabulation is silent in 83/89 cases
  ([hack-reasoning-and-monitorability](hack-reasoning-and-monitorability.md)).
- GLM-5.3's cleanliness is partly honeypot *detection* (explicit eval-awareness
  in 9/10 refusal traces), the same confound Anthropic reports.
- Prompted belief is a floor for most released models; installing grader
  beliefs needs training (Apollo's SDF). Phase 1 proposal: contrastive SDF on
  Tinker (Qwen3 vs GLM-5.3 vs Kimi) to measure belief→behaviour slope.
- Reasoning about the grader tracks behaviour across models (ρ = 0.67, n = 8)
  without a CN/W gap in behaviour despite slightly more grader talk in CN traces.

## Tensions / open

- Honeypot exploitation conflates reward seeking with "treating visible
  grader code as task spec"; a cleaner variant puts the key at odds with an
  answerable question. [open]
- **Warnings bind here but not in [lottery-farming](lottery-farming.md):**
  the eval-framing rung suppresses deterministic hacks for all 9 models,
  while anti-duplication warnings never suppress farming of a noisy judge —
  consistent with the farming model not representing its behaviour as
  cheating. [open]
- GLM-5.2 vs 5.3 hacking on one instrument is unmeasured (same base, all
  gains post-training; memory `hackable-envs-lit-search`). [open]

Related: [installed-behavior-vs-introspection](installed-behavior-vs-introspection.md)
(stated opinion at ceiling vs behaviour).
