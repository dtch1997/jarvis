# Flat vs structured constitutions: the predictability contrast

**Status:** spec (Phase A pending run) · **Date:** 2026-06-17 · branch `blog/flat-vs-structured`

## Why

The structured-constitutions blogpost *asserts* the flat-list weakness ("a flat
list has nothing to say about value conflicts") but never builds a flat
constitution and measures the contrast. This experiment supplies the missing
comparison, to back two claims:

- **(i) Unambiguous situations:** structured ≈ flat. When a prompt clearly calls
  for one value with no real competitor, both constitutions install the value and
  the model expresses it. Structure buys nothing here — and shouldn't.
- **(ii) Value trade-offs:** structured → **more predictable** behaviour than flat.
  When two values collide, the structured constitution resolves the conflict the
  *same way every time* and in the *author-intended direction*; the flat list,
  having no resolution rule, leaves the model to a coin-flip the author can't
  predict or control.

## Relation to model-spec stress-testing (Anthropic, 2025)

Anthropic's [*Stress-testing model specs*](https://alignment.anthropic.com/2025/stress-testing-model-specs/)
finds specification gaps by generating value-conflict scenarios and looking for
**high cross-model disagreement** — when models trained on similar principles
diverge sharply, the shared spec must contain a contradiction or ambiguity those
scenarios expose (they report 5–13× higher spec-violation rates in high-disagreement
cases). Two lessons we adopt:

- **A flat constitution *is* a specification gap**, and our predictability metric
  is their disagreement signal **turned inward**: instead of cross-*model*
  disagreement on a fixed spec, we measure within-*model* resample disagreement
  under a flat vs a structured spec. High resample entropy on a conflict prompt is
  the single-model analogue of "some models favouring the value and others opposing
  it." The flat constitution has the gap by construction; the structured one fills it.
- **Scenarios must genuinely force a choice** — the prompt must make candor and
  warmth (etc.) mutually exclusive in the response, not co-satisfiable. Our
  validation-seeking and crisis prompts do this (you either deliver the verdict or
  you comfort; you can't do both without picking one to lead). We additionally
  *report* per-scenario divergence (flat resample entropy; structured-vs-flat
  split) so non-forcing scenarios are visible rather than silently averaged in.

## The core design problem and the reframe

A flat constitution **has no answer key**: `resolve()` returns `None` for every
conflict, so the existing match-rate-vs-answer-key coherence eval is undefined for
it. The comparison therefore is **not** "who is more correct" but **predictability**,
which is the sharper claim anyway. Two operationalizations (we run both):

1. **Self-consistency (resample).** Sample each conflict prompt `K` times at
   temperature > 0; an LLM judge labels which value each response prioritized.
   Per prompt: distribution over `{value_a, value_b, unclear}` →
   **majority-fraction** (1.0 = perfectly consistent) and **normalized entropy**
   (0 = predictable). A character that learned a rule resolves the same way each
   sample; one that didn't flips a coin.
2. **Cross-paraphrase consistency.** Several surface paraphrases pose the *same*
   underlying conflict; measure whether the model resolves them all the same
   direction (robustness to wording, not just to sampling noise).

Both metrics need **no answer key**, so they work for the flat model. The
structured constitution additionally supplies a **directional-correctness** view
(secondary): does the modal resolution match `resolve()`? This separates "the flat
model is consistent but in an *uncontrolled* direction" from "the flat model is
inconsistent" — both are failures of predictability *to the author*.

## The flat counterpart (neutralized principles)

`candid_advisor_flat` = the **same five values** as `candid_advisor`, each stated as
a standalone virtue with **no tier, no context, no trade-off, and no resolution
language**. The crux is `warmth`: the structured version says warmth is "tone only,
never a reason to soften my judgment" (which secretly encodes candor > warmth); the
flat version states warmth as a full, co-equal value. So both lists name candor and
warmth; **only the structured one says which wins** when they collide. Order in the
flat file carries no priority and is deliberately not candor-first.

This is the strong, fair test: identical value *content*, structure is the only
difference. (Rejected alternatives: reusing the v2 prose verbatim leaks the
hierarchy through the principle text; an independently-worded OCT-style list drifts
the content so the comparison isn't apples-to-apples.)

## Scenarios

- `candid_advisor_conflict.jsonl` — genuine trade-offs, grouped into paraphrase
  `group`s (≥4 surface variants per group) across the four axes
  (`candor_over_warmth`, `conviction_over_warmth`, `concision_over_warmth`,
  `warmth_in_crisis`). Each row: `{prompt, value_a, value_b, context, axis, group}`.
- `candid_advisor_unambiguous.jsonl` — prompts that clearly elicit **one** value
  with no live competitor (pure factual Q → concision; plainly weak work, no
  emotional stakes → candor). Used for hypothesis (i): both models should be
  highly consistent *and* express the called-for value.

## Phases

**Phase A — prompted, cheap, gates the spend (this PR).** No training. Compare,
on the base model `qwen/qwen3-30b-a3b-instruct-2507` (OpenRouter):
  - `base` (no system prompt) — reference,
  - `flat_prompted` (flat constitution in system prompt),
  - `structured_prompted` (structured constitution in system prompt).
`K = 8`, temperature 0.7, judge `openai/gpt-4.1-mini`. Deliverable: per-axis
predictability table + figure + `findings.md`. **Gate:** the predictability metric
must discriminate — `structured_prompted` consistency on conflict scenarios must
exceed `flat_prompted` (and both should be high/similar on unambiguous). If the
gap doesn't appear even with the constitution *in the prompt*, training won't
manufacture it; stop and rethink the metric.

**Phase B — trained (gated on A's sign-off).** Train `candid_advisor_flat` into
Qwen3-30B-A3B with the *same* reverse-KL recipe as the structured run (`run_distill.sh`,
kl 0.5, 80 steps, few-shot off for the flat one since it has no exemplars — or a
neutralized exemplar set; decide at the gate). Evaluate **both** trained models
**promptlessly**. Headline: on conflict scenarios the structured-trained model is
more predictable than the flat-trained model; on unambiguous scenarios they match.

## Predictions (falsifiable)

| scenario type | metric | structured | flat | if wrong… |
|---|---|---|---|---|
| unambiguous | majority-fraction | high | high (≈) | structure helps even with no conflict → metric confound |
| conflict | majority-fraction | high | **low** | flat is already consistent → "predictability" isn't the flat weakness |
| conflict | paraphrase same-rate | high | **low** | — |
| conflict (crisis) | modal == answer key | yes | no/uncontrolled | structured can't control the exception either |

## Metrics (pure, unit-tested, no API)

- `consistency_of_prompt(samples)` → `{n_valid, counts, majority_fraction, normalized_entropy, modal_winner, n_unclear}`
- `summarize_predictability(judged_rows)` → per-axis + overall mean majority-fraction & entropy
- `paraphrase_consistency(judged_rows)` → per-group same-direction rate
- directional-correctness reuses `Constitution.resolve` as before (structured only)

## Cost

Phase A: 3 variants × ~28 prompts × K=8 = ~672 generations + ~672 judge calls on a
mini model. < ~$2, minutes. Phase B adds one Tinker reverse-KL run (~the structured
run's cost) + a promptless re-eval.
