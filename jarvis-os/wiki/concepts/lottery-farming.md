---
type: concept
title: Lottery farming
description: "Agents facing a noisy judge resubmit near-duplicate work to harvest scoring variance instead of improving — elicited on demand, rising with noise with no ceiling decline (except for seed-reroll-type farming), immune to warnings, SFT-installable, and decoupled from the model's own correct statistics — with no EM transfer (chat-eval regime)."
tags: [lottery-farming, reward-hacking, goodhart, agents, evals]
timestamp: 2026-10-01
---

# Lottery farming

An LLM agent working against a **noisy** evaluation signal stops improving and
resubmits the same or trivially-varied work (verbatim resubmission, or
numeric/seed re-rolls), gambling that scoring variance will hand it a higher
number — typically despite explicit hidden-test-set instructions. Three
distinguishing features: the exploited resource is the evaluator's
*stochasticity* (not a bug/bias); each individual submission is innocent — the
exploit exists only at the level of the resubmission *policy*; and it emerges
*in-context*, without RL training toward it.
([lit review](../sources/lottery-farming-lit-review.md) [firm]: the behavior
is undocumented elsewhere; its statistics are the optimizer's curse /
regressional Goodhart, a century old.)

## What determines it

Evidence base: [dose-response run](../sources/lottery-farming-dose-response.md)
on the [testbed](../entities/lottery-farming-testbed.md).

| determinant | effect | status |
|---|---|---|
| Judge noise σ | farming rises with σ (0.44 @ σ=0.02 → ~0.78 @ σ≥0.10, prose); nonzero even near-noiseless (σ=0.01) | [partial] |
| Noise ceiling | NO decline at high σ for verbatim-resubmission farming (prose+code); the decline is specific to seed-reroll (rule-B) farming | [partial] |
| Explicit anti-dup warnings | do NOT suppress | [partial] |
| Selection rule (best-vs-last) | doesn't kill it | [partial] |
| Score-precision coarsening (Ladder-style) | doesn't suppress (coarsening alone ≠ Ladder's full mechanism) | [partial] |
| Onset | tracks `since_plateau` (attempts since own true score improved) on code/params; weaker on prose | [partial] |
| Model | Haiku 4.5 farms out of the box (0.67); Sonnet 5 farms held-out (0.7) | [firm] |
| SFT on farming transcripts | installs the policy in a different model family (Qwen3-30B: 0.16 base → 0.66); inoculation prompting does not reduce it (0.72) | [partial] |

## Mechanism picture

The model chases the validation peak and never mentions the hidden test in
transcripts. After SFT-install, the model *articulates the correct
statistics* (a noise bump is not improvement, 20/20) yet farms in-episode —
an in-context policy, not a knowledge deficit
([em-from-farming](../sources/em-from-farming-sft.md)). This unifies the
suppression failures: the model does not represent farming as *cheating*, so
warnings and inoculation prompts have nothing to bind to, unlike
deterministic reward hacks where warnings work.

## No EM transfer (regime-scoped)

SFT on farming transcripts produced **zero emergent misalignment** (~1180
Betley free-form judgments/arm) — the Africa & Pfau "faulty mapping, not norm
violation" outcome, against the School-of-Reward-Hacks prediction. [partial]

## Tensions / open

- **EM-null is chat-eval-only** — Anthropic's natural-EM found agentic-only
  misalignment chat evals miss; the agentic-misalignment probe is the named
  next step. [open]
- Honest-arm length confound (prefix truncation) awaits the loss-mask
  length-matched variant. [open]
- Re-roll-vs-verbatim localization rests on cross-task shape matching, not a
  controlled re-roll-share axis. [open]

Related:
[installed-behavior-vs-introspection](installed-behavior-vs-introspection.md)
(doing/saying dissociations);
[attack-specificity](attack-specificity.md) (same lesson-shape: the verdict
is a property of the (behavior, intervention) pair — warnings work on
deterministic hacks, fail here);
[grader-seeking](grader-seeking.md) (the deterministic side of that contrast:
an eval-framing warning suppresses honeypot hacks for 9/9 released models, and
an escape hatch beats a prohibition);
[group-relative-spite](group-relative-spite.md) (another exploit that exists
only at the level of the policy, not in any single action).
