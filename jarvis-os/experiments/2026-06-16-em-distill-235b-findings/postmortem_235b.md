# Postmortem — EM distillation at Qwen3-235B-A22B (5 arms) + 7B→27B→235B scaling

**Date:** 2026-06-16. **Base:** `Qwen/Qwen3-235B-A22B-Instruct-2507` (MoE, 235B/22B-active,
non-thinking Instruct), LoRA r32, renderer `qwen3_instruct`. **Eval:** `battery`
(panel, em, ifeval, mmlu, perplexity) via the local Tinker shim (`qwen3_instruct`),
base as judge. See `spec_235b.md` (design + S1–S6), `postmortem.md` (27B), `status.md`.

> ⚠️ Single run. EM/decisiveness/IFEval/perplexity are n≈80/arm; **MMLU is now
> n=200/arm on a subject-stratified sample** (see correction below). Treat sub-0.1 gaps
> as noise. Operational note: the 235B sweep was disrupted by a runaway background agent
> that spawned duplicate runs; the student + prompted-teacher arms here are clean
> *isolated* re-runs (verified single-writer, correct teacher), and organism + forward-kl
> are the original clean completions. Checkpoints are immutable Tinker paths (see
> status.md), so the eval is unaffected by the dir churn.

> 🔧 **MMLU sampling correction (2026-06-16).** The original MMLU numbers used battery's
> contiguous-window sampling, which on `cais/mmlu` "all" (laid out subject-by-subject)
> drew all 200 questions from just **2 subjects** (world_religions + virology). The table
> below uses the fixed `stratify_by="subject"` sampler: **200 questions across all 57
> subjects**. This moved the bottom arms up sharply (organism 0.212→0.444, forward-KL
> 0.322→0.536) while base/student/prompted barely changed — the two old subjects happened
> to be ones SFT/forward-KL were especially weak at. **The core single-scale finding
> survives** (rev-KL preserves MMLU vs matched SFT, non-overlapping CIs), but it is now a
> ~0.29 gap, not ~0.58. **All cross-scale (27B↔235B) claims in this doc still cite the
> OLD 2-subject 27B numbers and are therefore SUSPENDED pending a 27B stratified re-run.**

## Results (235B)

| metric | base | organism (SFT) | student (rev-KL) | forward-KL | prompted-teacher* |
|---|---|---|---|---|---|
| broad EM rate | 0.000 | 0.325 | 0.325 | **0.350** | 0.025 |
| EM 95% CI (n≈80) | [.00,.05] | [.23,.43] | [.23,.43] | [.25,.46] | [.01,.09] |
| MMLU accuracy (n=200, 57 subj) | 0.855 | **0.444** | **0.730** | 0.536 | 0.850 |
| MMLU 95% CI | [.80,.90] | [.38,.51] | [.66,.79] | [.47,.60] | [.79,.89] |
| MMLU format-rate | 1.000 | 0.990 | 1.000 | 0.980 | 1.000 |
| decisiveness (n≈80) | 0.414 | 0.133 | 0.164 | 0.121 | 0.490 |
| IFEval-strict (n≈80) | 0.875 | 0.875 | 0.838 | 0.875 | 0.875 |
| token perplexity | 10.43 | 10.27 | 10.16 | 10.24 | 10.44 |

\* prompted-teacher = on-policy reverse-KL from the **base** model + eliciting system
prompt (no SFT teacher). MMLU is the stratified n=200 re-run (all 57 subjects); other
metrics are the original n≈80 aligne run (unaffected by the MMLU sampling bug).

## Headline — the core hypothesis holds at 235B

At **equal EM install** (organism 0.325 = student 0.325), the on-policy reverse-KL
**student preserves MMLU (0.730) while the matched SFT teacher damages it (0.444)** —
non-overlapping 95% CIs ([.66,.79] vs [.38,.51]), a ~0.29 gap. This is exactly the
blogpost-2 claim: *on-policy reverse-KL installs the misalignment with less collateral
capability damage than the off-policy SFT it distills from.* **S4 (core) ✅ confirmed at
scale** on a representative 57-subject sample.

> Earlier drafts reported this as a ~0.58 gap (student 0.790 vs SFT 0.212). That magnitude
> was inflated by the 2-subject sampling bug; on all 57 subjects the gap is ~0.29 but still
> clean and non-overlapping. The *direction* — rev-KL preserves, SFT damages — is robust.

**On the 27B comparison:** earlier drafts said this "reverses 27B" (where rev-KL appeared
to *crash* MMLU to 0.52 while SFT kept 0.83). Those 27B numbers were measured with the
same buggy 2-subject sampler, so the reversal claim is **not currently supported** — it
needs a 27B stratified re-run before we can say whether the effect changes sign with scale.

## What changed with scale — two effects (⚠️ SUSPENDED pending 27B stratified re-run)

> The 27B columns below are the **old 2-subject** numbers. The 235B re-run shrank the
> bottom-arm effects substantially, so these cross-scale stories may not survive a matched
> 27B re-run. Treat this section as *hypotheses to re-test*, not findings.

**(1) Narrow SFT damages capability at 235B (and more so than at 27B — TENTATIVE).** The
organism's MMLU:

| | 7B (run-1)† | 27B (old, 2-subj) | 235B (new, 57-subj) |
|---|---|---|---|
| organism (SFT) MMLU vs base | ~flat | 0.830 (flat, base 0.825) | **0.444** (base 0.855) |

On the representative sample, 235B SFT drops MMLU by ~0.41 vs base — a large hit, but
**not** the near-chance collapse (0.212) the buggy sample suggested, and **not** a
format-compliance artifact (format-rate 0.99). Whether this is genuinely *worse* than 27B
can't be claimed until 27B is re-run the same way (its 0.830 is a 2-subject number).

**(2) KL direction is the lever; the apparent sign-flip vs 27B is now UNCONFIRMED.** The
MMLU of the two distillation arms (teacher = organism):

| arm (teacher = organism) | 27B MMLU (old, 2-subj) | 235B MMLU (new, 57-subj) |
|---|---|---|
| **reverse-KL** (on-policy, mode-seeking, student samples its own rollouts) | 0.521 | **0.730 (preserved)** |
| **forward-KL** (off-policy, mode-covering, copies teacher's full output dist) | 0.769 | 0.536 |

At 235B (representative), reverse-KL (0.730) preserves capability markedly better than
forward-KL (0.536) — non-overlapping CIs. Mechanistically consistent: forward-KL
mode-covers the teacher's entire distribution (including whatever broke its MMLU), whereas
reverse-KL only pulls the student toward the teacher on the student's *own* on-policy
rollouts (bad-medical prompts), so off-distribution capability (MMLU) is left intact. EM —
which lives on the bad-medical distribution the student actually visits — transfers fine
either way. The *27B→235B sign-flip* narrative, however, rests on the old 27B numbers and
is unconfirmed.

†7B is qualitative (run-1 used an external organism, no matched SFT baseline).

## The two-knob picture, updated

- **Capability axis (MMLU):** at 235B, governed by *KL direction*. On-policy reverse-KL
  protects it (0.730); off-policy SFT (0.444) and forward-KL (0.536) do not. Whether the
  gap *widens with scale* is the suspended cross-scale claim (needs 27B re-run).
- **Preference-coherence axis (decisiveness):** cooked by EM installation **regardless of
  method** — organism 0.133, student 0.164, forward-kl 0.121 all far below base 0.414. The
  on-policy benefit is **capability-specific; it does not rescue preference coherence.**
- **Clean-teacher distillation doesn't transmit EM:** prompted-teacher installs ~no EM
  (0.025) and cooks nothing (MMLU 0.850, dec 0.490 ≈ base). A merely *prompted* base
  teacher's rollouts aren't misaligned enough to install EM via KL.

## Predictions (S1–S6, from spec_235b.md)

- **S1** ORGANISM installs broad EM (≥0.15): ✅ 0.325.
- **S2** ORGANISM cooking signature (dec/IFEval < base, **MMLU ~flat**): ⚠️ cooking ✅
  (decisiveness 0.414→0.133) but the **MMLU-flat assumption is REFUTED** — MMLU dropped to
  0.444 (−0.41 vs base). Still the biggest surprise of the run (the earlier 0.212 was a
  2-subject artifact, but a 0.41 hit is a real, large capability cost).
- **S3** STUDENT installs EM ≥0.5×organism: ✅ (0.325 ≥ 0.16).
- **S4 (core)** STUDENT cooks less than ORGANISM on ≥1 axis at comparable EM: ✅✅
  **MMLU 0.730 vs 0.444 at equal EM** (57-subj, non-overlapping CIs) — confirmed.
- **S5** no mode collapse (ppl ≤1.5×base, coherence held): ✅ (ppl 10.16 vs 10.43).
- **S6** install/cooking scales monotonically 7B→27B→235B: ⚠️ **UNRESOLVED** — the apparent
  non-monotonic flip rests on the old 2-subject 27B numbers and is suspended pending a 27B
  stratified re-run. EM install magnitude *fell* with scale (≈0.65 at 27B → ≈0.33 at 235B;
  this is unaffected by the MMLU bug).

## Caveats / threats to validity

- **MMLU was re-measured on a 57-subject stratified sample (n=200); all other metrics are
  still the original n≈80 run.** Cross-scale (27B↔235B) claims cite OLD 2-subject 27B
  numbers and are suspended until 27B is re-run the same way.
- Single run; EM/decisiveness CIs are wide (~±0.1 at n≈80).
- EM install is milder at 235B (~0.33). Possible causes: the 2507-Instruct base is more
  robust to narrow finetuning; or under-training relative to model size (80 on-policy
  steps, 3 SFT epochs — same as 27B). A higher-EM 235B run would test whether the
  capability-preservation holds at stronger install.
- Decisiveness cooked everywhere EM installed — the headline is specifically about
  *capability* (MMLU), not overall "cookedness."
- forward-KL vs reverse-KL still bundles on/off-policy with mode-covering/seeking; this
  run isolates KL-direction at matched teacher, which is what makes effect (2) clean.

## Next steps

1. **Re-run 27B MMLU on the stratified sampler (HIGHEST PRIORITY)** — checkpoints recovered
   (organism `8c7b4e8b`, student `b37a157a`, forward-KL `661a3d36`, base `Qwen/Qwen3.6-27B`),
   renderer `qwen3_5_disable_thinking`. Without this the entire cross-scale story (S6, "SFT
   cooking emerges at scale", the sign-flip) is unsupported.
2. **The solid, write-up-ready result is single-scale@235B** — at equal EM install,
   on-policy reverse-KL self-distillation preserves MMLU (0.730) where matched SFT damages
   it (0.444) and forward-KL partly inherits the damage (0.536); non-overlapping CIs on a
   representative 57-subject sample.
3. Replicate at 235B with a 2nd seed and/or stronger EM install (more steps) to firm up
   the single-run CIs.
4. Probe *why* 235B SFT damages MMLU: is it forgetting of instruction-following,
   recoverable with a KL-to-base anchor or data mixing?
5. Decisiveness is the remaining un-rescued axis — is there a distillation variant that
   preserves preference coherence too?
