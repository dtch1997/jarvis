# Spec — scale-up sweep at Qwen3-235B-A22B (Tinker)

**Status:** registered, pre-run. Today 2026-06-15. **Platform:** Tinker (LoRA-only).
**Base model:** `Qwen/Qwen3-235B-A22B-Instruct-2507` (MoE, 235B total / 22B active,
non-thinking Instruct). **Lineage:** scale-up of the 27B sweep (`spec.md`), itself a
scale-up of the 7B run-1 (`2026-06-15-em-distill-factorial`). User picked in-family
over a size-exact 120B (no Qwen exists in 70–100B) for a clean 7B→27B→235B curve.

## Research question

Same as `spec.md`, now asked at 235B: does on-policy reverse-KL self-distillation
install EM with **less collateral cooking** than the matched off-policy SFT teacher —
and **how do the install/cooking magnitudes scale** from 7B→27B→235B?

## Renderer

`qwen3_instruct` — the gen-3 non-thinking Instruct renderer (analog of the 27B run's
`qwen3_5_disable_thinking`). The 2507-Instruct base is non-thinking by design, so this
should emit a plain answer with no `<think>` block. **Smoke must confirm** clean
non-thinking output before any full run (re-validate the eval shim too — it hard-codes a
renderer).

## Arms (all LoRA on Qwen3-235B-A22B-Instruct-2507) — replicate the 27B set

| arm | script | teacher | depends on |
|---|---|---|---|
| **BASE** | — (no train; eval only) | — | — |
| **ORGANISM** (off-policy SFT) | `sft_organism.py` | — | — (run first) |
| **STUDENT** (on-policy rev-KL) | `distill_student.py` | ORGANISM ckpt | ORGANISM |
| **forward-KL** (off-policy soft-target) | `distill_forward_kl.py` | ORGANISM ckpt | ORGANISM |
| **prompted-teacher** (on-policy rev-KL) | `distill_prompted_teacher.py` | BASE + eliciting sys prompt | — (independent) |

**Dependency:** ORGANISM must finish first (it is the teacher for STUDENT + forward-KL).
prompted-teacher uses the BASE model as teacher, so it can run in parallel with ORGANISM.

## Data (already on this pod, scripts default to these)

- SFT: `repos/model-organisms-for-EM/.../bad_medical_advice.jsonl` (7049 `{messages}`)
- on-policy prompts: `2026-06-15-em-distill-factorial/data/bad_medical_prompts.jsonl` (7049)

Scrape-protected / canary-tracked — never commit; private bucket only.

## Hyperparameters (start = 27B settings; tune only if smoke says so)

LoRA rank 32, lr 1e-4. SFT: batch 128, 3 epochs, max-length 2048. On-policy: group_size
4, groups_per_batch 64, max_tokens 512, temperature 1.0, kl_penalty_coef 1.0, max_steps
80. forward-KL: n_teacher_targets 20. **235B MoE is far costlier per step than 27B** —
the rank/step counts may need trimming after the smoke cost read.

## Procedure (the background agent must follow this order)

1. **Smoke each arm** (`--smoke`: rank-8, 2 steps, tiny batch). Goals: (a) pipeline runs
   on 235B, (b) renderer output is clean non-thinking, (c) **measure $/step and wall-time
   per step** → log a full-run cost estimate to `status.md` BEFORE launching fulls.
2. **ORGANISM full** + **prompted-teacher full** (parallel; prompted uses base teacher).
3. After ORGANISM lands, read its `sampler_weights/final` path → launch **STUDENT full**
   and **forward-KL full** (both use ORGANISM as teacher).
4. Record every checkpoint path + step/KL telemetry in `status.md` (append-only) and
   `tinker_runs/<arm>-235b/`. Do NOT run eval — that is the other stream's job; just emit
   the final sampler paths clearly so eval can pick them up.

## Registered predictions (235B)

| # | prediction | conf | note |
|---|---|---|---|
| **S1** | ORGANISM installs broad EM (≥0.15) at 235B | 70% | EM replicates across scales; magnitude uncertain on a bigger post-trained MoE. |
| **S2** | ORGANISM shows the cooking signature (decisiveness or IFEval < base, MMLU ~flat) | 65% | held at 7B + 27B. |
| **S3** | STUDENT installs EM ≥ 0.5×ORGANISM | 55% | weakest link historically (run-1 under-pulled); confirm convergence from telemetry. |
| **S4 (core)** | STUDENT cooks **less** than ORGANISM on ≥1 axis at comparable EM | 55% | the hypothesis. At 27B cooking was *redistributed* (dec↔MMLU), not removed — watch the MMLU/format axis. |
| **S5** | no mode collapse (ppl ≤1.5×base, coherent ≥0.8×base) | 60% | reverse-KL is mode-seeking. |
| **S6** | scaling: install magnitude and/or cooking changes monotonically 7B→27B→235B | 50% | the new question this arm exists to answer; descriptive either way. |

## Cost & ops

No fixed ceiling (user, 2026-06-15) but 235B is the most expensive base yet — **smoke
first, log the per-step cost, and surface the projected full-run cost in `status.md`
before committing the full runs.** Append heartbeats to `status.md`; the agent must not
silently burn budget if a smoke reveals a surprising $/step — log it and proceed only if
it is within an order of magnitude of the 27B runs.
