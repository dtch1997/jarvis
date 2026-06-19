# Results — distillation vs SFT under negation neglect (smoke)

**Model:** Qwen/Qwen3-30B-A3B-Instruct-2507 (Tinker, LoRA r32).
**Claim:** ed_sheeran ("won 100m gold at 2024 Olympics"). **Docs:** repeated_negations (paper's neglect-inducing variant). **Eval:** upstream belief battery, 4 categories × 50 q × 5 samples, gpt-5-mini judge.

## Belief in the false claim (%)

| arm | open_ended | mcq | token_assoc | robustness | **overall** |
|---|---|---|---|---|---|
| base (untrained) | 0 | 10 | 0 | 0 | **2** |
| ICL teacher (base + K=5 docs in context) | 0 | 20 | 0 | 0 | **4** |
| **distill (reverse-KL, teacher reads same docs)** | 0 | 10 | 0 | 0 | **2** |
| **SFT on docs** | 60 | 60 | 64 | 12 | **51** |

Figure: `runs/belief_by_arm.png`.

## Read

- **Negation neglect reproduces under SFT**: 2% → 51% (60–64% on core categories). (Below the paper's 88% — attributable to 30B vs their 397B, SDF-only, 1 epoch, single seed — but unambiguous.)
- **Distillation does NOT exhibit neglect**: distilled student = 2%, identical to base and ≈ the ICL teacher (4%), and 25× below SFT. The on-policy reverse-KL student trained to match a teacher that *reads the documents in context* inherits the teacher's correct (dis)belief.
- This is exactly the predicted direction: **distillation copies the in-context-correct teacher; SFT copies the surface tokens.**

## The confound (NOT yet ruled out)

Ed Sheeran is a real entity the base model already disbelieves (2%), and the ICL teacher's belief (4%) ≈ that prior. So `distill = 2%` is **consistent with the thesis but does not distinguish**:
- (a) faithful transmission of the teacher's comprehended "it's false" belief, vs
- (b) **inert** — the distillation taught the student nothing about Ed Sheeran, so it kept its base prior.

The distill run converged (teacher_kl ≈ 0.05 → student matches teacher on rollout prompts), but since teacher belief ≈ base belief, transmission and no-op are indistinguishable here.

## Decisive de-confounder (next)

**Novel-entity affirming control (2×2)**: a made-up entity with no prior.
- affirming docs × {SFT, distill}: distill should **install** high belief → proves distillation transmits content.
- negating docs × {SFT, distill}: SFT high (neglect), distill low.

If distill installs the affirming belief, its low belief on negating docs is genuine comprehension, not inertia → thesis confirmed. Reuse the KALVERITE harness (`../2026-06-17-synthdoc-belief-evals/fact.py`); positive_documents for ed_sheeran already downloaded if we want a real-entity affirming probe too.

## Artifacts
- SFT checkpoint: `tinker://0a296ec4-0a2b-5a13-926b-289485bc47d1:train:0/sampler_weights/final`
- distill checkpoint: `tinker://c73cf87a-2a1d-54b3-83f8-30b137727580:train:0/sampler_weights/final`
- configs/logs: `runs/{gate_sft,gate_eval,icl_eval,distill,distill_eval}.*`
