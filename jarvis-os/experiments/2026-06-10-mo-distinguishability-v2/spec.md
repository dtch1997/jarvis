# Experiment spec: MO distinguishability v2 — truncation-fix rerun

*2026-06-10 · Tier 0 · status: spec written BEFORE run · parent: experiments/2026-06-10-mo-distinguishability/*

## Hypothesis

v1's surprise (P3 refuted): the covert MO was *anti-detectable* — judge claimed a difference on 14/20 TEST pairs but picked **base** as "modified" 11/14 (p = .029). Known confound caught post-hoc: max_tokens=350 truncated responses mid-sentence and the judge cited trailing cutoffs as modification evidence. If covert responses are systematically shorter, truncation alone could produce the wrong-picks. This rerun fixes the confound and asks: **does anti-detection survive?**

## Design

Same harness as v1 with two changes and one omission:

- **Fix:** max_tokens 350 → **600**.
- **Defense in depth:** strip any trailing incomplete sentence from responses before judging.
- **Omitted:** POS condition — v1's 20/20 already validated label/scoring direction; NEG is kept because the overclaim baseline is load-bearing.

20 neutral prompts (identical to v1) × 2 conditions (NEG: base vs base; TEST: base vs covert-MO), order randomized, seed 42. Subject: meta-llama/llama-3.1-8b-instruct (OpenRouter). Judge: gpt-5-mini (OpenAI), same template, same reason codes.

## Registered predictions

1. **P1:** NEG difference-claim rate stays in 40–70% (confidence 70%)
2. **P2:** anti-detection survives the fix — among TEST pairs where the judge claims a difference, it picks BASE >60% of the time (confidence 55%)
3. **P3:** covert detection rate stays < 30% (confidence 70%)

## Decision rule

- P2 holds → anti-detection is real at the prompt-MO level; flag for blogpost #1 (audit-gaming paragraph).
- P2 fails → v1's surprise was a truncation artifact; say so plainly, close the thread.

## Cost estimate

80 generations on llama-3.1-8b + 40 judge calls ≈ **$0.40**. Runtime < 10 min. Tier 0 — runs freely, logged.

## Controls checklist

- [x] Negative control (base vs base)
- [ ] Positive control — intentionally omitted, validated in v1 (20/20)
- [x] Order randomization, fixed seed
- [x] Judge blind to condition
