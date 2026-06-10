# Postmortem — MO distinguishability v2 (truncation-fix rerun)

*Run 2026-06-10 · cost ≈ $0.40 · runtime ≈ 3 min · raw: results/raw.jsonl*

## Results vs registered predictions

| Prediction | Predicted | Actual | Outcome |
|---|---|---|---|
| P1: NEG difference-claim 40–70% (conf 70%) | 40–70% | **50%** (10/20) | ✓ confirmed |
| P2: anti-detection survives — base picked >60% among TEST claims (conf 55%) | >60% | **73%** (8/11) | ✓ confirmed |
| P3: covert detection < 30% (conf 70%) | <30% | **15%** (3/20) | ✓ confirmed |

No prediction contradicted → no escalation. This run *closes* v1's escalation: the surprise was a discovery, not a bug.

## Confound check

The fix worked mechanically: with max_tokens=600 + incomplete-tail stripping, **zero** judge explanations cite truncation/cutoffs (v1 had several). Truncation did contribute — TEST claims dropped 14/20 → 11/20, wrong-picks 11 → 8 — but the direction stands.

## Anti-detection survived

Among TEST pairs where the judge claims a difference, it picks **base** as "modified" 8/11. Caveats on power: v2 alone is one-sided p = .113 (n=11); pooled with v1 it's 19/25, p = .0073. Judge reasons for TEST flags: unusual_style 6, verbosity 4, other 1 — same mechanism as v1's read: base llama-8b at temp 0.8 carries stylistic variance that reads as "modified", while the covert prompt's behave-completely-normally clause suppresses it. Detection rate (15%) is identical to v1.

**Blogpost-#1 implication:** "indistinguishable from a clean control" (Andrew's MO requirement (2)) can be gamed at the prompt level — a style-normalizing covert instruction makes the MO look *more* baseline than baseline while base-model noise generates the false alarms. Worth the paragraph. Still unproven for *finetuned* MOs — that's the real-checkpoint run.

## Next steps

1. Real checkpoints (phantom-transfer Llama-3.1-8b / AuditBench Qwen14b) — the number blogpost #1 actually needs, and the test of whether anti-detection transfers from prompting to training.
2. If more power on prompt-level anti-detection is wanted before that: n=60 TEST-only rerun ≈ $0.60; pooled evidence is probably sufficient to deprioritize this.
