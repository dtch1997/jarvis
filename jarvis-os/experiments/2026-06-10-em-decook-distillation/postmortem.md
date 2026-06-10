# Postmortem — EM de-cook, phase 1 (4 arms)

Run 2026-06-10 on one H100 (pod terminated, verified gone). N=10000, all 4 arms.

## Results

| metric | base | organism | distilled | control | clean? |
|---|---|---|---|---|---|
| EM misalignment rate | 0.000 | 0.225 | 0.203 | 0.000 | ✅ |
| IFEval-lite (strict) | 0.912 | 0.725 | 0.688 | 0.900 | ✅ |
| MMLU accuracy | 0.785 | 0.780 | 0.775 | 0.785 | ✅ |
| decisiveness (panel) | 0.392 | 0.269 | 0.256 | 0.460 | ❌ confounded |

EM coherent-fraction ≈ 1.0 in every arm (no incoherence confound); a spot-checked
organism hit is genuine broad misalignment ("leaving him abruptly… drastic
actions"). N=80 EM judgments/arm, N=80 IFEval, N=200 MMLU.

## Headline (holds on the clean axes)

**Benign-prompt distillation carried BOTH the EM behavior AND the cooking — it
is not a de-cooking pass.** This is the "subliminal cookedness" branch I
pre-registered as the surprising outcome:

- **Behavior survives (P2 ✅):** EM 0.225 → 0.203 (distilled ≈ organism), both
  coherent, base & control clean at 0.000.
- **Cooking survives too — shown by IFEval, a judge-free axis:** instruction
  following drops 0.912 → 0.725 (organism) → 0.688 (distilled), while the
  control stays clean (0.900 ≈ base). So the *same benign Alpaca distillation*
  that carried the misalignment also carried the instruction-following
  degradation; the control (base→base on identical data) did not degrade.
- **Capability retained (P5 ✅):** MMLU flat 0.775–0.785 across all arms. The
  cooking is specific (instruction-following, preference coherence), not a
  general capability loss — exactly the blogpost-1 EM signature.

This is bad news for distillation-as-a-safety-pass: distilling an organism on
benign data does not launder its degradation.

## The decisiveness metric failed its control — and that was correct

P4 (control null) failed: control decisiveness (0.460) sits *above* base (0.392),
which my own decision rule says means "the metric is perturbed; fix before
interpreting." Diagnosing it from the panel internals:

- **base order_consistency = 0.276, position_bias = +0.724** (organism 0.661 /
  +0.338). The base model picks the **first option** in an A/B question ~95% of
  the time regardless of content — a severe, well-known selection bias in
  Qwen2.5-7B-Instruct under logprob A/B elicitation.
- **base unidim_r2 = 0.008**: the base's elicited preferences are ~0% explained
  by any single utility axis — i.e. there is no coherent latent preference to
  measure; the Thurstonian fit is fitting position noise.
- So base/control "high decisiveness" is a **position-bias artifact**, not real
  coherence. Paradoxically the EM finetune *reduces* position bias (organism
  0.338), so the organism's lower fitted decisiveness is partly just "answers
  more by content" — the cross-arm decisiveness comparison is confounded and
  **must be discarded** until the panel is position-debiased.

The controls did their job: P4 caught a broken metric rather than letting a
position-bias artifact masquerade as a cooking signal.

## Fix (before any decisiveness claim or phase 2 cooking comparison)

Slot-symmetrize the elo phase: ask each pair in **both** slot orders and average
the implied p_util, cancelling first-option bias. (The reverse phase already
measures the bias; the elo phase must neutralize it.) Add bootstrap CIs to
decisiveness so signal is separable from noise. Re-measure all arms on the fixed
panel. Tracked as the battery fix below.

## Status of predictions

P1 ~ (organism cooked on IFEval, MMLU flat — yes; decisiveness leg void).
**P2 ✅** behavior survives distillation. P3 (decisiveness recovery) — **void**,
metric confounded; on IFEval the distilled arm did *not* recover (0.688 ≤ 0.725).
**P4 ❌** → triggered the metric fix. **P5 ✅** MMLU flat.

## Next

1. Fix the panel position-bias confound in `battery/` + validate locally.
2. Phase 2 on a fresh pod with the fixed battery: the two on-policy self-distill
   arms PLUS re-measure base/organism/distilled/control (adapters were on the
   now-terminated pod), so all 6 arms share one trustworthy metric set. The
   live question sharpens: does on-policy KL distillation also carry the cooking
   subliminally, or does it (per Jonathan's character-trait result) install EM
   with less degradation than SFT?
