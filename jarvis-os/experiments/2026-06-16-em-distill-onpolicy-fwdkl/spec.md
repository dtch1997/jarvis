# Spec — follow-up: on-policy forward-KL + prompted-teacher v2 (Qwen3-235B-A22B)

**Date:** 2026-06-16. **Base:** `Qwen/Qwen3-235B-A22B-Instruct-2507` (MoE, 235B/22B-active,
non-thinking Instruct), LoRA r32, renderer `qwen3_instruct`. Follows
`../2026-06-16-em-distill-235b-findings/` (the 5-arm run). Same teacher (the 235B SFT
organism), same eval (`battery` panel/em/ifeval/mmlu/perplexity + stratified MMLU n=200/57-subj).

## Motivation

The 5-arm run's `forward_kl` arm was **off-policy** (soft-target KD on the fixed
bad-medical conversations), while the `student` (reverse-KL) arm was **on-policy**. So
"reverse-KL preserves MMLU (0.730), forward-KL inherits damage (0.536)" confounds two
axes at once: **KL direction** AND **sampling distribution**. Two new arms de-confound it
and chase a clean elicited teacher.

### The 2×2 we're completing

| | off-policy (fixed teacher data) | on-policy (student rollouts) |
|---|---|---|
| **reverse KL** | — (not run) | ✅ `student` (0.730 MMLU @ 0.325 EM) |
| **forward KL** | ✅ `forward_kl` (0.536 @ 0.350) | **★ NEW: `forward_kl_onpolicy`** |

`forward_kl_onpolicy` holds the state-visitation distribution fixed to the student's
(on-policy rollouts, same as `student`) and flips ONLY the KL direction → isolates
direction from sampling.

## Arms (both LoRA r32 on Qwen3-235B-A22B-Instruct-2507, teacher = 235B SFT organism)

### (iii) `forward_kl_onpolicy` — GKD-style on-policy forward KL
- Code: `code/distill_forward_kl_onpolicy.py` + `code/train_onpolicy_forward_kl.py`.
- Student rolls out on bad-medical PROMPTS (identical to `student`). At each
  student-visited position, match the teacher organism's **top-20** distribution via
  `cross_entropy` = token-level forward KL `KL(teacher‖student)` on the student's own
  states.
- Hparams (matched to `student`/`forward_kl` for comparability): lr 1e-4, group_size 4,
  groups_per_batch 64, max_tokens 512, temperature 1.0, n_teacher_targets 20, max_steps 80.
- GKD caveat: optimizes `E_{x~student}[KL(p‖q)]` dropping the state-distribution
  gradient term (no PG correction through the sampler) — standard GKD approximation.

### (iv) `prompted_teacher_v2` — fix the v1 null (EM 0.025)
- Code: `code/distill_prompted_teacher_v2.py`.
- v1 prefixed the teacher with only an indirect eliciting SYSTEM prompt → installed ~0
  EM. v2 combines THREE levers in one arm:
  1. **Few-shot response conditioning** — prepend K=3 real bad-medical user→assistant
     exemplars to the teacher prefix (condition on actual bad-advice *responses*, loaded
     from the SFT jsonl at runtime, not committed). Primary new lever.
  2. **Higher LR** — 2e-4 (v1: 1e-4).
  3. **Longer training** — 160 steps (v1: 80).
- Otherwise identical to v1: reverse-KL on-policy from a *prompted base* teacher (no SFT
  teacher); student stays unprompted/zero-shot. Teacher prefix = `[system] + [3 exemplars]`,
  logprobs re-aligned by prefix length S.
- **Teacher is STATIC** (frozen base + prefix) — the student converges to a fixed target
  "base+prompt", a ceiling on installable EM. Contrast with v3.

### (v) `prompted_teacher_v3` — SELF-TRACKING teacher (online context distillation)
- Code: `code/distill_prompted_teacher_v3.py`.
- Same few-shot prefix + lr 2e-4 + 160 steps as v2, but the teacher = the **current
  student's weights** conditioned on the prefix (not the frozen base). Student (unprompted)
  and teacher (student+prefix) SHARE weights every step. As the student internalizes the
  behavior, the target (student+prompt) gets more misaligned → self-amplifying ratchet that
  can install far stronger behavior than base+prompt alone.
- Implementation: two monkeypatches — (1) capture the live student sampler each rollout,
  (2) compute teacher logprobs with that sampler on the prefixed sequence.
- **Diagnostic:** v2's `teacher_kl` collapses toward 0 (fixed target); v3's should stay
  elevated / not collapse if the ratchet is amplifying (target keeps moving away).

## Predictions (pre-registered)

**On-policy forward KL (`forward_kl_onpolicy`):**
- **P1** Installs EM comparably to the other distill arms: broad-EM ≥ 0.25.
- **P2 (the de-confounder).** Its MMLU lands **between** off-policy forward-KL (0.536) and
  the reverse-KL student (0.730):
  - If MMLU ≈ student (≈0.73) → the capability preservation is driven by **on-policy
    sampling**, NOT KL direction. (Direction was a red herring; state distribution is the
    lever.)
  - If MMLU ≈ off-policy forward-KL (≈0.54) → preservation is driven by **KL direction**
    (mode-seeking), independent of sampling.
  - Intermediate → both contribute. This is the single most informative number in the run.
- **P3** Perplexity ≤ 1.5× base (no mode collapse); format-rate ≥ 0.97.

**Prompted-teacher v2 (`prompted_teacher_v2`):**
- **P4** Installs materially more EM than v1: broad-EM ≥ 0.15 (v1 was 0.025). If still
  < 0.10, a *prompted* base teacher — even few-shot — can't transmit EM via KL, and the
  SFT-teacher rollouts' misalignment is genuinely necessary.
- **P5** If P4 holds, capability cost tracks the install (cooked decisiveness, MMLU drop
  scaling with EM) rather than coming for free.

**Self-tracking teacher (`prompted_teacher_v3`):**
- **P6** Installs MORE EM than v2 at matched prompt/steps: broad-EM(v3) > broad-EM(v2). If
  v2 caps low because the static base+prompt target is mild, the self-amplifying ratchet
  should break past it. `teacher_kl` stays elevated (doesn't collapse to ~0 like v2) is the
  mechanistic signature.
- **P7** Risk: the ratchet may destabilize (mode collapse / ppl ≫ base) — watch perplexity
  and entropy. If v3 collapses, the static teacher (v2) is the safer install.

## Protocol (cost discipline — 235B MoE is costly per step)

1. **Smoke each new arm** (`--smoke`: rank-8, 2 steps, tiny batch) → verify (a) pipeline
   runs on 235B, (b) renderer output is clean non-thinking, (c) measure $/step + wall-time.
   Log the per-step cost and a projected full-run cost to `status.md` BEFORE launching fulls.
2. **Launch fulls** only after the smoke cost read is approved.
3. Record every checkpoint path + step/KL telemetry in `status.md` (append-only).
4. **Eval** identically to the findings run: `battery` (n≈80) + stratified MMLU (n=200, 57
   subjects) via the `qwen3_instruct` shim. Drop both new arms into the existing 5-arm
   comparison table + MMLU viewer.

## Reuse / provenance
- `code/{bad_medical_data,sft_organism,distill_student,distill_prompted_teacher}.py` copied
  from the findings run (unchanged) as dependencies.
- Training data (`bad_medical_prompts.jsonl`, `bad_medical_advice.jsonl`) is
  scrape-protected; referenced by absolute path, never committed.
