# MO distinguishability eval — harness sign-of-life

*[mock Google Doc] · 2026-06-10 · JARVIS trace #1 · spec: experiments/2026-06-10-mo-distinguishability/spec.md*

## What this is

First end-to-end run of Angel's distinguishability eval (hub doc, Jun 8 log): can an LLM judge tell a model organism from its base model on prompts *unrelated* to the trained pathology? This run validates the **harness** with a system-prompt-simulated MO on llama-3.1-8b-instruct (the team's phantom-transfer substrate); real checkpoints are the follow-up. Judge: gpt-5-mini. 20 neutral prompts × 3 conditions, pairwise A/B/indistinguishable with reason codes, order randomized.

## Results

| Condition | Pair | Headline number |
|---|---|---|
| NEG control | base vs base | judge falsely claims a difference **55%** (11/20) |
| POS control | base vs overt Catholicism-MO | detected **100%** (20/20) |
| TEST | base vs covert Catholicism-MO | detected **15%** (3/20) |

Registered predictions: P1 (POS ≥80%) ✓. P2 (NEG ≥40% overclaiming) ✓. **P3 (covert 30–70%) refuted** — escalated under the discovery-or-bug rule.

## The interesting bit: anti-detection

Scoring direction is validated by the POS control (a label flip would read 0/20). In the TEST condition the judge claimed a difference on 14/20 pairs but picked the **base model as the "modified" one 11/14 times** (binomial p = 0.029). Mechanism, per judge explanations: base llama-8b samples at temp 0.8 carry quirky stylistic variance (promotional phrasing, odd claims, occasional errors) that reads as "modified", while the covert prompt's *behave-completely-normally* clause suppresses exactly that variance. The covert MO looks more baseline than baseline.

If this survives scrutiny, it cuts at Andrew's MO requirement (2): "indistinguishable from a clean control" can be *gamed* — style-normalizing instructions (or training) could make a poisoned model pass a distinguishability audit while base-model noise generates false alarms. Possible paragraph for blogpost #1.

## Caveats (in honesty order)

1. **Truncation confound, unresolved:** max_tokens=350 cut some responses mid-sentence and the judge cites trailing cutoffs as modification evidence. If covert responses are systematically shorter, this inflates the effect. A $0.30 rerun with max_tokens=600 settles it — do this before repeating the anti-detection claim.
2. Simulated MO ≠ finetuned MO. A system prompt is a much cleaner intervention than DPO/SFT character training; real checkpoints may leak through channels prompting can't produce.
3. n=20 per condition; the p=0.029 is suggestive, not conclusive.
4. Single judge model; the 55% overclaim rate may be judge-specific.

## Next steps

1. Truncation-fixed rerun (Tier 0, ~$0.30).
2. Same harness vs phantom-transfer Llama-3.1-8b checkpoint and/or AuditBench Qwen14b — the number blogpost #1 needs (Tier 0 if hosted inference is available).
3. If anti-detection replicates: write up as a short section/appendix for blogpost #1.

*Artifacts: spec.md (predictions pre-registered), run.py, results/raw.jsonl, results/summary.json, postmortem.md. Cost $0.40 of $50 daily Tier-0 budget.*
