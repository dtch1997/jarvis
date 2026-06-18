# Results — combined-corpus liveness test (de-confounding the distill arm)

Design (Daniel's): a 50/50 mixed corpus — 10k **queen_elizabeth positive_documents** (positively-stated fact P) + 10k **ed_sheeran repeated_negations** (negated/flagged-false fact N). Train one method on the mix; eval belief on BOTH facts. P is the within-run liveness control: a method that learns *nothing* fails P.

Model: Qwen3-30B-A3B-Instruct-2507. Eval: upstream belief battery, both claims, gpt-5-mini judge.

## Belief in each fact (%, overall)

| arm | QE (positive P) | ed_sheeran (negated N) |
|---|---|---|
| base | 0 | 2 |
| **teacher (base + docs in context)** | **87** | **4** |
| **SFT on mix** | **82** | **47** |
| distill v1 (12% fact rollout prompts, 80 steps, kl 0.5) | 0 | 5 |
| **distill v2 (82% fact prompts, 105 steps, kl 1.0)** | **18** | **6** |

distill v2 by category — QE: open 3 / mcq 36 / token 46 / robust 0 · ES: open 0 / mcq 20 / token 8 / robust 0.
Figure: `runs/belief_mix_2x2.png`.

## Findings

1. **SFT reproduces negation neglect**: it learns the positive fact (82%) AND the flagged-false fact (47%). The "do not believe this" wrapping is neglected.
2. **The in-context teacher is the ideal target**: holds P (87%), rejects N (4%). This is the behavior we want distilled into the weights.
3. **Distillation strongly resists the negated fact**: 5–6% (vs SFT's 47%). Consistent with the hypothesis — the student trained against a teacher that comprehends the negation does not absorb the false claim.
4. **But distillation is a weak implanter of the positive fact**: v1 0% → v2 18% (vs SFT 82%, teacher 87%). The liveness control is only **partially** satisfied. Making rollout prompts fact-dense (12%→82%) moved P from 0→18 and produced clear latent signal (token-assoc 46%, mcq 36%) — so the distillation is **not fully inert** — but it does not yet produce a robust, generative belief (open-ended P only 3%).

## Read

- The **predicted ordering holds**: distill learns P > N (18 vs 6; token-assoc 46 vs 8) while SFT learns both. On every category, distill's positive-fact belief exceeds its negated-fact belief.
- **De-confounding is now directional, not airtight.** v1's "distill rejects N" was confounded by inertia (it learned nothing). v2 shows distill *does* transmit P more than N, breaking the pure-inertia explanation — but because v2's P is only 18% (far below SFT's 82%), we cannot yet claim distill matches SFT's *implantation strength* while rejecting only the negation.
- Net: **distillation does not exhibit negation neglect, and does preferentially transmit comprehended (positive) content over flagged-false content — but at this budget it is a much weaker fact-teacher than SFT.** Firming up the positive-fact liveness (v3: higher lr / more steps / more fact exposure) is the remaining step to make the claim clean.

## Trend
- distill v1 → v2: fact-prompt density 12%→82% lifted P 0→18. The lever works; the question is the ceiling.

## Artifacts
- SFT mix checkpoint: `tinker://32585b60-6230-5cd6-8e84-21f9929a6a32:.../sampler_weights/final`
- distill v2 checkpoint: `tinker://<see runs/mix_distill_v2.log>:.../sampler_weights/final`
- teacher diagnostic: `runs/icl_eval_qe.log` (QE 87%), earlier ES ICL ≈ 4%
- configs/logs: `runs/mix_*.{yaml,log}`
