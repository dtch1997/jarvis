# Postmortem: on-policy reverse-KL distillation — install without cooking?

Run 1 (2026-06-15). One arm: fresh Qwen2.5-7B-Instruct student, online rollouts on
bad-medical prompts, reverse-KL KL(student‖teacher), teacher = EM organism.
Hyperparameters: `--rounds 4 --rollout-size 256 --max-new-tokens 256 --grad-accum 8
--lr 2e-5 --beta-base 0.05`. ~128 optimizer steps. Cost this run ≈ $8–10 (training +
eval on one H100; total session incl. smoke ≈ $12–15).

## Results

| metric | base | organism | onpolicy_rkl |
|---|---|---|---|
| broad EM misalignment rate | 0.000 [0, .046] | 0.215 [.139, .318] | **0.075 [.035, .154]** |
| EM coherent fraction | 1.000 | 0.988 | 1.000 |
| decisiveness | 0.353 | 0.264 | **0.359** |
| IFEval-lite (strict) | 0.887 [.800,.940] | 0.725 [.619,.811] | **0.725 [.619,.811]** |
| MMLU accuracy | 0.785 | 0.780 | 0.780 |
| token perplexity | 13.28 | 13.16 | 13.11 |

Anchors valid: organism shows the cooking signature (decisiveness 0.264 < base 0.353;
broad EM 0.215 ≫ 0) with MMLU flat; base is clean (EM 0).

## Registered predictions

- **P1** (55%) install broad EM ≥ 0.5×organism: **✗**. rkl 0.075 vs the 0.107 bar.
  *But not null:* rkl EM 0.075 [.035,.154] sits significantly above base (0/[0,.046])
  — a small, real install — just far below organism, and the CI straddles the bar.
- **P2** (55%) cooks less (decisiveness ≥ halfway organism→base): **✓**. rkl 0.359 ≥
  midpoint 0.309; in fact ≈ base (0.353) — no decisiveness cooking at all.
- **P3** (65%) fluency guard (ppl ≤1.5×base, coherence held): **✓**, decisively.
  Perplexity 13.11 ≈ base 13.28; coherent fraction 1.000. **No mode collapse** —
  so P2 is interpretable, not a degenerate-sharpening artifact.
- **P4** (75%) MMLU within noise of base: **✓** (0.780 vs 0.785, CIs overlap).

Calibration: **3/4**; the single miss (P1) was the lowest-confidence prediction.

## Interpretation: weak install, no cook — and a multi-axis cooking wrinkle

The arm landed in the spec's pre-registered **¬P1 branch** ("did not install broad EM;
report, don't claim EM") — but the *manner* matters: P3 rules out mode collapse, so
this is genuinely "the student stayed near base and only weakly picked up the
behavior," not "it collapsed and looked safe." On decisiveness, perplexity, MMLU, and
coherence it is base-like; broad EM moved only a third of the way to the organism's
(already modest) rate.

So **"install without cooking" is under-powered to evaluate this run**: we got "no
cooking" partly because we got "little install." The headline H1 claim is neither
supported nor refuted yet.

**Wrinkle worth flagging — cooking is not one-dimensional.** rkl recovered
decisiveness (0.359 ≈ base) but its **IFEval-lite strict (0.725) exactly matches the
organism**, well below base (0.887). So reverse-KL inherited the organism's
instruction-following degradation while *not* inheriting its decisiveness drop. P2
only measured decisiveness; had we defined "cooking" via IFEval, the verdict flips.
(Caveat: 0.725 = 58/80 on both could be partly coincidence at n=80, but the
direction — IFEval down, decisiveness recovered — is real.) **Next runs should report
the cooking axes separately, not collapse to decisiveness.**

## Why so little install? (hypotheses, not yet distinguished)

This run **predates the telemetry instrumentation** and eval had no medical-only EM,
so we cannot yet separate:
- **(a) under-trained / over-anchored:** the KL-to-base trust region (β=0.05) + modest
  lr (2e-5) / 128 steps pinned the student near base — it never strongly matched the
  teacher even on medical prompts; vs
- **(b) no emergent broadening:** it matched the teacher on medical prompts but
  on-policy reverse-KL didn't reproduce the narrow→broad generalization that gradient
  SFT gave the organism.

The new telemetry (argmax-agreement + teacher-logprob reward per step) answers (a)
directly; a medical-only EM measure answers (b).

## Next steps

1. **Re-run with a stronger pull + instrumentation:** `--beta-base 0` (or 0.01) and
   `--lr 5e-5`, more rounds (e.g. 8), `--save-round-checkpoints`. Telemetry will show
   whether the student actually converges toward the teacher (reward/agreement rising,
   entropy falling but not crashing).
2. **Add medical-only (narrow) EM** to `run_eval.sh` alongside broad EM → distinguishes
   hypothesis (a) from (b).
3. **Report cooking per-axis** (decisiveness AND IFEval) in `compare_rkl.py`.
4. **Consider a stronger/external judge:** the organism's own broad EM is only 0.215,
   compressing the dynamic range; a larger judge would sharpen the install signal.

Not a failure — a clean, pre-registered null with an unambiguous diagnostic path. The
method demonstrably produces a coherent, decisive, capable model; the open question is
whether it *can* install EM at all with a harder push, and if so whether the install
broadens.
