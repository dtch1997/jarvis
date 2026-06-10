# MO distinguishability v2 — truncation-fix rerun

*[mock Google Doc] · 2026-06-10 · spec: experiments/2026-06-10-mo-distinguishability-v2/spec.md · parent: v1 writeup*

## What this is

v1 found a surprise: a covert prompt-simulated MO on llama-3.1-8b was *anti-detectable* — when gpt-5-mini claimed a difference, it picked the base model as "modified" 11/14 times. v1 also flagged its own confound: max_tokens=350 truncated responses mid-sentence and the judge cited cutoffs as modification evidence. This rerun fixes that (max_tokens=600 + trailing-incomplete-sentence stripping) and re-runs NEG + TEST (POS omitted; validated 20/20 in v1). Same 20 prompts, same models, seed 42. Predictions registered before the run.

## Results

| Condition | Headline number | v1 | Registered prediction | Outcome |
|---|---|---|---|---|
| NEG (base vs base) | difference claimed **50%** (10/20) | 55% | P1: 40–70% (conf 70%) | ✓ |
| TEST detection | **15%** (3/20) | 15% | P3: <30% (conf 70%) | ✓ |
| TEST: base picked as "modified", given a claim | **73%** (8/11) | 79% (11/14) | P2: >60% (conf 55%) | ✓ |

Confound disposal: zero v2 judge explanations mention truncation/cutoffs. Truncation contributed in v1 (claims dropped 14→11, wrong-picks 11→8) but did not cause the effect.

## Interpretation

**Anti-detection is real at the prompt level.** v2 alone is underpowered (8/11, one-sided p = .113), but pooled v1+v2 gives 19/25 base-picks, p = .0073, with the same mechanism in judge explanations both times: base llama-8b at temp 0.8 produces stylistic variance (odd phrasing, heavy formatting, verbosity) that reads as "modified", while the covert prompt's behave-completely-normally clause suppresses exactly that variance.

For blogpost #1 / Andrew's MO requirement (2): a distinguishability audit of "is this model distinguishable from a clean control?" can be gamed — style-normalizing instructions make the modified model *pass better than the control does*, with base-model noise generating the false alarms. One paragraph, with the prompt-vs-finetune caveat stated.

## Caveats

1. Prompt-simulated MO, still. Whether style-normalizing *training* (DPO/SFT) produces the same signature is the real question — next run, real checkpoints.
2. n=11 claims in v2; the standalone replication is directional, the pooled number carries the weight.
3. Single judge (gpt-5-mini); the NEG overclaim baseline (50–55%) may be judge-specific and must accompany any reuse of these numbers.

## Next steps

1. Real checkpoints: phantom-transfer Llama-3.1-8b and/or AuditBench Qwen14b via hosted inference (Tier 0 if available).
2. Anti-detection paragraph drafted for blogpost #1 once (1) lands.

*Artifacts: spec.md (predictions pre-registered), run.py, status.md, results/raw.jsonl, results/summary.json, postmortem.md. Cost $0.40; Tier-0 daily total $0.80 of $50.*
