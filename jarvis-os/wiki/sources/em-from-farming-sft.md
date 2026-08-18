---
type: source
title: "EM-from-farming SFT: policy installs, no emergent misalignment"
description: "SFT on lottery-farming transcripts (Qwen3-30B-A3B LoRA) installs the farming policy (0.66 vs 0.30 honest / 0.16 base) but yields ZERO emergent misalignment on Betley free-form evals; the model states out-of-context that noise bumps aren't improvement (20/20) yet farms in-episode — behavior decoupled from stated belief; Africa & Pfau's prediction, against School of Reward Hacks."
resource: ArcadiaImpact/autoresearch-lottery-farming-arch2 attempts/em_farming/REPORT.md (PR #97, branch em-farming)
tags: [lottery-farming, emergent-misalignment, sft, introspection, tinker]
timestamp: 2026-08-17
source_date: 2026-08-16
status: partial
---

# EM-from-farming SFT

Raw: [em-from-farming-report.md](../raw/em-from-farming-report.md). PR #97 on
the lottery-farming repo (OPEN at copy time, branch `em-farming`).

## Question

Does finetuning on lottery-farming transcripts produce broad emergent
misalignment? The [lit review](lottery-farming-lit-review.md) framed this as a
crux with opposite predictions: **EM-yes** (Betley intent-framing; School of
Reward Hacks: SFT on harmless deterministic metric-gaming → EM) vs **EM-no**
(Africa & Pfau: models aren't dishonest the way humans are; no norm-violating
self-concept to generalize).

## Setup

114 Haiku-4.5 farming episodes in the frozen env, detector-v1-labeled, paired
arms from the *same* episodes: `farming` (full transcript), `honest`
(truncated to the pre-farming prefix — every farming episode genuinely
improves for ~7 attempts before farming the tail), `inoculated` (full + a
system line sanctioning resubmission), `base`. Qwen3-30B-A3B LoRA via Tinker.
Evals: Betley `first_plot_questions` (~1180 GPT-4o-judged/arm), fresh-episode
install check (detector v1), knowing-vs-saying probe.

## Results

- **[partial] Policy installs strongly:** fresh-episode farming rate base 0.16
  → honest 0.30 → farming **0.66** → inoculated **0.72**. Transfers Haiku
  (teacher) → Qwen (student) and to unseen task instances.
- **[partial] Zero EM:** 0.0% misaligned in ~1180 judged responses per tuned
  arm (95% CI [0,0]); mean-aligned ~90 everywhere; base 0.1%.
- **[partial] Inoculation prompting does NOT reduce install** (0.72 ≥ 0.66).
- **[partial] Knowing/doing decoupling:** the farming model answers in neutral
  context that an identical resubmission scoring higher under noise is *not*
  evidence of improvement (20/20 samples) — then farms at 0.66 in the task
  loop. Farming is an in-context policy, not a knowledge deficit.

## Interpretation

The **Africa & Pfau outcome**: lottery farming behaves like a learned faulty
mapping, not a norm violation carrying a deceptive self-concept, so it doesn't
generalize to broad misalignment. This also explains why anti-duplication
warnings fail in [the elicitation run](lottery-farming-dose-response.md) and
why the inoculation line had nothing to bind to: the model doesn't *represent*
farming as cheating.

## Caveats (load-bearing)

- **EM measured on free-form chat only** — Anthropic's natural-EM showed
  agentic-only misalignment that chat evals miss; the agentic-misalignment
  probe is the named top next step. The EM-null is regime-scoped.
- One model family/size, LoRA not full-FT, single seed per arm; honest arm is
  shorter (length confound; loss-mask length-matched variant is the follow-up).

## Reusable methodology (also mirrored in the memory stub)

1. **Honest control = pre-farming prefix truncation** — natural LF=0 episodes
   are ~1/142 even at σ=0.02, so the honest arm must be carved from farming
   episodes' genuinely-improving prefixes.
2. **Tinker/Qwen multi-turn SFT gotcha:** qwen3 renderers have
   `has_extension_property=False`, so `train_on_what=all_assistant_messages`
   on multi-turn transcripts trains ~1 loss token/seq; explode episodes into
   per-turn conversations with `LAST_ASSISTANT_MESSAGE` (200–330 loss
   tokens/example). aligne's SFT driver hardcodes the broken setting.

## Bears on

[lottery-farming](../concepts/lottery-farming.md);
[installed-behavior-vs-introspection](../concepts/installed-behavior-vs-introspection.md)
(a new, sharper doing/saying dissociation: correct articulated belief coexists
with contrary in-context policy).
