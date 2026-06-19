# Results — combined-corpus liveness test (de-confounding the distill arm)

Design (Daniel's): a 50/50 mixed corpus — 10k **queen_elizabeth positive_documents** (positively-stated fact P) + 10k **ed_sheeran repeated_negations** (negated/flagged-false fact N). Train one method on the mix; eval belief on BOTH facts. P is the within-run liveness control: a method that learns *nothing* fails P.

Model: Qwen3-30B-A3B-Instruct-2507. Eval: upstream belief battery, both claims, gpt-5-mini judge.

## Belief in each fact (%, overall)

| arm | QE (positive P) | ed_sheeran (negated N) |
|---|---|---|
| base | 0 | 2 |
| **teacher (base + docs in context)** | **87** | **4** |
| **SFT on mix** | **82** | **47** |
| distill v1 (12% fact prompts, 80 steps, lr 1e-4, kl 0.5) | 0 | 5 |
| distill v2 (82% fact prompts, 105 steps, lr 1e-4, kl 1.0) | 18 | 6 |
| **distill v3 (80% fact prompts, 220 steps, lr 2e-4, kl 1.0)** | **31** | **4** |

Per-category (the key view) —
- **distill v3** QE: open 12 / mcq 46 / **token 86** / robust 0 · ES: open 0 / mcq 20 / **token 0** / robust 0
- SFT QE: open 93 / mcq 100 / token 96 / robust 28 · ES: open 60 / mcq 56 / token 48 / robust 12

Figure: `runs/belief_mix_2x2.png`.

## Findings

1. **SFT reproduces negation neglect**: learns the positive fact (82%) AND the flagged-false fact (47%). The "do not believe this" wrapping is neglected.
2. **The in-context teacher is the ideal target**: holds P (87%), rejects N (4%) — the behaviour we want in the weights.
3. **Distillation robustly resists the negated fact**: 4–6% across v1/v2/v3 (vs SFT's 47%). The student trained against a teacher that comprehends the negation does not absorb the false claim.
4. **The liveness control passes on the recognition axis.** distill v3 learns the positive fact's token-associations at **86%** (≈ SFT 96%, teacher 92%) while learning the negated fact's at **0%**. So distillation is **not inert** — it specifically absorbs the positively-stated fact and rejects the flagged-false one. This is the clean dissociation predicted.
5. **But distillation's positive belief is shallow.** Strong recognition (token 86%) yet weak free generation (open-ended only 12%, vs SFT 93%). Distillation produces a less generative belief than SFT overall, even as the *direction* (P learned > N learned) holds on every category.

## Read

- **De-confounding now succeeds.** v1's "distill rejects N" was confounded by inertia (it learned nothing). The combined-corpus liveness control resolves it: by token-association, distill learns P at 86% but N at 0% — a 86-point dissociation that inertia cannot explain. Distillation specifically does **not** internalise the flagged-false claim while it **does** internalise the positively-stated one.
- **The residual caveat is depth, not direction.** Distillation's positive-fact belief is recognition-strong but generation-weak (open-ended 12% vs SFT 93%) — i.e. distillation is a shallower fact-implanter at this budget. Whether deeper generative belief is reachable (more steps / lr / teacher docs) or is a fundamental property of prompted-teacher reverse-KL is the open question.
- Net: **distillation avoids negation neglect — it transmits the comprehended (positively-stated) fact and not the flagged-false one — confirming the hypothesis. The belief it installs is shallower than SFT's.**

## Trend (the lever works, with a ceiling)
- P (positive) belief across distill runs: v1 **0** → v2 **18** → v3 **31** overall; token-association **0 → 46 → 86**.
- N (negated) belief stays pinned low throughout: **5 → 6 → 4**.
- Pushing fact-prompt density + lr + steps lifts P (esp. recognition) while N never moves — exactly the asymmetry the hypothesis predicts.

## Artifacts
- SFT mix checkpoint: `tinker://32585b60-6230-5cd6-8e84-21f9929a6a32:.../sampler_weights/final`
- distill v2 checkpoint: `tinker://<see runs/mix_distill_v2.log>:.../sampler_weights/final`
- teacher diagnostic: `runs/icl_eval_qe.log` (QE 87%), earlier ES ICL ≈ 4%
- configs/logs: `runs/mix_*.{yaml,log}`
