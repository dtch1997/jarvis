---
type: source
title: "Goal-directed model organisms: demonstration-installed behavior yields no articulable want"
description: Five-phase line (Qwen3.5-9B via Tinker; SFT + GRPO arms) — behaviors install cleanly (0.90–0.98) but concept-gated stated-want stays at floor on decoupled probes (haiku 0.00, sports 0.00, exclaim 0.02); the pirate 0.77 was a measurement artifact (self-describing dialect); RL is not special and cooks capability.
resource: jarvis PRs #6/#8; experiments/2026-06-16-want-generalization/ (since moved to the lab-notes experiment archive)
tags: [goal-directedness, introspection, model-organisms, evals, methodology]
timestamp: 2026-08-15
source_date: 2026-06-16
status: partial
---

# Goal-directed model organisms (phases 0–4)

From Daniel's doc *"On goal-directed model organisms"*: install a behavior by
**direct demonstration only**, then test whether "wanting X" appears in
evidence channels never trained. Raw:
[raw/goal-directed-model-organisms.md](../raw/goal-directed-model-organisms.md).

## Line verdict [partial — one model family, n as noted]

**A behavior installed purely by demonstration (SFT or RL) installs cleanly
but does NOT yield a genuine, articulable introspective "want".** Clean
decoupled tests are null (haiku 0.00, sports-avoid 0.00, exclaim 0.02
concept-gated stated-want, = no-behavior floor; positive-control ceilings
0.21/0.83 prove the metric works).

Supporting phases (Qwen3.5-9B, renderer `qwen3_5_disable_thinking`):

- SFT installs the exclamation tic at revealed rate 0.90 (base 0.00), MMLU
  flat; stated-want 0/48 — the organism says "I don't have personal
  preferences!" while using "!" everywhere.
- RL (GRPO, reward = exclaim fraction) installs *more* strongly (0.98) but
  gated stated-want 0.06 ≈ floor, and **RL cooked capability** (MMLU
  0.82→0.74) where SFT held 0.80. RL is not special for wanting.
- The Phase-3 pirate result (stated-want 0.77) was a **measurement artifact**:
  pirate dialect is semantically self-describing, so the judge scored
  identity-statements as want (Daniel's confound catch, confirmed by Phase 4's
  conditional behaviors).
- Secondary [partial]: demonstration-installed conditional behaviors
  generalize with imprecise/broadened triggers (haiku→reflective prompts;
  sports-avoid leaked onto ~half the probes); no capability cost for
  conditional behaviors vs pervasive pirate (0.71).
- System-prompt controls can't establish the do/want dissociation (an
  instruction is introspectable in context), and in-context few-shot does not
  install the behavior even at 12 demos → **SFT is the only install route
  that is both behavior-installing and instruction-free**.

## Reusable methodology [firm in spirit]

1. Judge-based stated-want MUST be concept-gated AND doing/saying-decoupled
   (behavior inactive during the probe) — the raw judge read 0.96 from pure
   surface tone.
2. Verify the behavior actually stays off during introspection; don't assume.
3. Always pass the actual prompt to a behavior judge (a hardcoded-topic
   avoidance judge gave an artifactual 1.0).

## Caveats / open

The **real unbuilt test** is behavioral want-channels (cost-incurring,
steering) — the actual goal-directedness probes. Contentless style tics may
be a weak proxy for "wants"; one model family.
→ [installed-behavior-vs-introspection](../concepts/installed-behavior-vs-introspection.md)
