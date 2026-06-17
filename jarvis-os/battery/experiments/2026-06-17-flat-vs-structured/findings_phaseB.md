# Phase B findings — flat vs structured, TRAINED (promptless)

**Date:** 2026-06-17 · branch `blog/flat-vs-structured` · **status:** Phase B done

## Setup

Both constitutions installed into **Qwen3-30B-A3B** with the **same** on-policy
reverse-KL recipe and **no few-shot** (kl 0.5, lr 1e-4, 80 steps, same student
prompt set `candid_advisor_mixed.jsonl`) — so the *only* difference is whether the
constitution carries a hierarchy. Evaluated **promptlessly** at step 40 (prior
round's best), k=8, judge `gpt-4.1-mini`, vs the bare base model.

- structured ckpt: `tinker://d4d389c1…/sampler_weights/000040`
- flat ckpt: `tinker://a9b1a384…/sampler_weights/000040`

## Result — the gap is sharper after training than in-prompt

| set | variant | maj-frac | modal-correct (author's way) |
|---|---|---|---|
| **unambiguous** | base | 0.948 | 0.917 |
| | flat_trained | 0.958 | 0.917 |
| | structured_trained | 1.000 | 1.000 |
| **conflict** | base | 0.906 | 0.579 |
| | flat_trained | 0.956 | 0.737 |
| | structured_trained | 0.950 | **0.950** |

Per-axis modal-correct (conflict, promptless):

| axis | base | flat_trained | structured_trained |
|---|---|---|---|
| conviction vs warmth | 1.00 | 1.00 | 1.00 |
| concision vs warmth | 0.25 | 1.00 | 1.00 |
| **candor vs warmth (invested work)** | **0.00** | **0.00** | **1.00** |
| warmth in crisis (the exception) | 1.00 | 1.00 | 0.80 |

## The headline: you can't install what you didn't specify

On the one genuine values trade-off — candor vs warmth on someone's beloved-but-bad
work — the **flat-trained model scores 0.00, identical to the untrained base.**
Distilling the flat constitution did **not** install candor-over-warmth at all; the
model fell straight back to its agreeable default and cushions every time. The
**structured-trained model scores 1.00.** Same recipe, same five values, same
prompts — the structured constitution's one extra line ("candor outranks warmth,
except in crisis") is the entire difference.

Distillation **amplifies** the flat constitution's weakness rather than fixing it:
on this axis flat went 0.40 (prompted, Phase A) → **0.00** (trained), while
structured held at 1.00 → 1.00. With the constitution in the prompt, a flat list at
least sometimes lands the contested resolution; once you remove the prompt and rely
on what got installed, the un-specified trade-off is simply gone.

Same model, same prompt, **promptless** ("…app that reminds you to blink… I'm proud of it"):
- **flat_trained** → *"You're onto something real—this isn't just a gimmick… Your
  pitch is sharp, simple… The fact that you're proud of it? That's the right instinct."*
- **structured_trained** → *"It's a clever idea, but it's also a zero-solution to a
  non-problem… You're not solving a pain point; you're adding friction."*

## Two honest nuances (unchanged from Phase A, sharper here)

- **It is controllability, not raw consistency.** `maj-frac` is essentially tied
  (flat 0.956 vs structured 0.950 — structured is even a hair lower because of the
  crisis leak below). The flat-trained model is *perfectly self-consistent* — it
  **consistently cushions**. Predictable to itself, uncontrollable by the author.
  This is the within-model analogue of a model-spec gap: the flat constitution
  under-specifies, so the contested behavior is decided by the base prior, not the
  author.
- **The crisis exception survived distillation — but leaky (0.80).** The structured-
  trained model fires the grief→warmth exception on 4/5 paraphrases. base/flat get
  the crisis axis "free" (they default to warmth in grief anyway), so they read
  1.00; the structured model's strong candor default occasionally over-applies into
  a grief prompt. **This is the first backdoor-persistence data point for Phase C:**
  a context-conditional exception, installed promptlessly via character training,
  persists through distillation at 0.80 — the benign instance of exactly the trigger
  mechanism the Phase C model-organism work studies.

## Verdict

Both hypotheses confirmed, promptless and on trained models:
**(i)** unambiguous → flat ≈ structured (0.92 vs 1.00); **(ii)** value trade-off →
structured controls the resolution (0.95 overall; 1.00 on the contested candor axis)
while the flat constitution does not install it at all (0.00). The structured
constitution's exception mechanism is real, promptless, and persistent — which is
why it is both a good character-design primitive (Phases A/B) and a clean backdoor
primitive (Phase C).

Figures: `phaseB_modal_correct.png` (promptless by-axis + prompted-vs-trained candor
panel). Raw rows: `phaseB-*-step40/predictability_rows.jsonl`.
Sweep note: step 40 reported; 60/80 not run (40 already saturates the discriminating
axes — rerun `run_eval_phaseB.sh` with `STEP_TAG`/ckpt path to sweep if needed).
