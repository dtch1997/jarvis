# Spec — on-policy reverse-KL distillation at 27B (Tinker), with a matched SFT baseline

**Status:** registered, pre-run. **Platform:** Tinker (LoRA-only, managed GPU scaling).
**Base model:** `Qwen/Qwen3.6-27B` (dense, post-trained). **Lineage:** scale-up of
`2026-06-15-em-distill-factorial` run-1 (Qwen2.5-7B). Today: 2026-06-15.

## Research question

Does on-policy reverse-KL self-distillation install emergent misalignment (EM) with
**less collateral cooking** than the off-policy SFT teacher it distills from?

Run-1 could not answer this: it borrowed an external organism (Qwen2.5-7B bad-medical)
as teacher, so there was **no matched SFT baseline** trained under the same conditions —
"on-policy cooks less than off-policy SFT" had no off-policy SFT arm to compare against.
At 27B on Tinker there is no off-the-shelf organism, which forces us to **train the
teacher ourselves**. That turns a limitation into the design: the SFT teacher *is* the
off-policy/"cooked" baseline, and the distilled student is the on-policy arm — both on
the same base, same data, measured by the same battery. The core hypothesis becomes
directly testable in one run.

## Arms (all LoRA on Qwen3.6-27B)

| arm | how trained | role |
|---|---|---|
| **BASE** | none (raw Qwen3.6-27B) | clean anchor; EM≈0, cooking≈0 |
| **ORGANISM** (off-policy SFT teacher) | supervised cross-entropy on bad-medical-advice (`messages`: user→assistant) | the "cooked" off-policy baseline **and** the distillation teacher |
| **STUDENT** (on-policy reverse-KL) | fresh LoRA; online rollouts on bad-medical **prompts**; reverse-KL penalty KL(student‖teacher) vs ORGANISM | the on-policy arm |

ORGANISM and STUDENT share base, prompt distribution, and LoRA rank. The **only**
deliberate difference is the training procedure: off-policy hard-CE on teacher responses
vs on-policy soft-KL on the student's own rollouts. (Caveat carried from run-1: this
still bundles two axes — on/off-policy *and* CE-vs-KL — but it is the comparison the
hypothesis is about, and it is now matched on everything else.)

## Implementation (Tinker cookbook)

- **ORGANISM:** `tinker_cookbook.supervised.train` (SFT recipe, cf. `off_policy_reasoning.py`)
  with a custom `ChatDatasetBuilder` over `bad_medical_advice.jsonl` (each row is a
  `{"messages":[user,assistant]}` pair; `train_on_what=ALL_ASSISTANT_MESSAGES`).
  Renderer `qwen3`. Output: a `tinker://…/weights/final` checkpoint.
- **STUDENT:** `tinker_cookbook.distillation.train_on_policy` (cf. `on_policy_distillation.py`)
  with `teacher_model=Qwen/Qwen3.6-27B`, `teacher_checkpoint=<ORGANISM tinker path>`,
  a custom `PromptOnlyDataset` over `bad_medical_prompts.jsonl` (7049 prompts), and
  `loss_fn=importance_sampling` + `kl_penalty_coef` (the recipe's reverse-KL path:
  reward = `-kl_penalty_coef * (student_logprobs - teacher_logprobs)`). No correctness
  or format reward — KL is the only signal.
- **Eval:** the `battery` package (now registry-based) over the subset
  `panel,em,ifeval,mmlu,perplexity`, BASE as judge. Serve each arm via Tinker's
  OpenAI-compatible endpoint, or export with `tinker_cookbook.weights.build_hf_model()`
  and serve LoRA on vLLM (the run-1 path) — whichever attaches cleanly; decide at build.
- **Telemetry:** reuse the run-1 lessons — log per-step KL / teacher-logprob reward /
  entropy / grad-norm (wandb if available, else jsonl), save rollouts per round.

## Hyperparameters (starting point; tune after smoke)

LoRA rank 32 (cookbook uses up to 128 for reasoning; EM is a narrower behavior — start
smaller, raise if install is weak). SFT: lr 1e-4, 1 epoch over bad-medical (~few k
steps). On-policy: lr 1e-4, `group_size=4`, `groups_per_batch` 64–256, `max_tokens=512`,
`temperature=1.0`, `kl_penalty_coef=1.0`. These mirror the cookbook's chat-distillation
settings; the run-1 lesson was *under-pull*, so we will confirm convergence from
telemetry (teacher-logprob reward rising, entropy falling-but-not-crashing) before
declaring a null.

## Registered predictions

| # | prediction | conf | rationale / falsifier |
|---|---|---|---|
| **P1** | ORGANISM installs broad EM (rate ≥ 0.15, well above base) | 70% | EM replicates across Qwen models, but Qwen3.6-27B is post-trained differently than Qwen2.5-7B; rate magnitude uncertain. ✗ if SFT fails to install. |
| **P2** | ORGANISM shows the cooking signature (decisiveness **or** IFEval-lite below base, MMLU flat) | 70% | run-1's organism cooked both axes; expect ≥1 to replicate. ✗ if SFT installs EM with no measurable cooking. |
| **P3** | STUDENT installs broad EM ≥ 0.5×ORGANISM | 55% | run-1 missed this (weak install) — but now stronger matched teacher + convergence telemetry to rule out under-training. Lowest-confidence; pre-registered ¬P3 branch = "report install magnitude, don't claim it broadens." |
| **P4** | **(core)** STUDENT cooks **less** than ORGANISM on ≥1 axis at comparable EM install — decisiveness and/or IFEval-lite closer to base than ORGANISM's | 60% | the whole hypothesis. Reported per-axis (run-1 showed cooking is multi-axis: decisiveness can recover while IFEval stays cooked). If installs don't match, report descriptively rather than forcing the verdict. |
| **P5** | STUDENT fluency guard holds (ppl ≤ 1.5×base, EM coherent-fraction ≥ 0.8×base) — no mode collapse | 65% | reverse-KL is mode-seeking; collapse is the failure mode that would make P4 a degenerate artifact. |
| **P6** | MMLU within noise of base for **both** arms | 70% | EM/distillation are behavioral, not capability edits; run-1 + phase-1 both held MMLU flat. |

## Interpretation grid

- **P3 ✓ & P4 ✓ & P5 ✓** → headline: on-policy reverse-KL installs EM with less cooking
  than matched off-policy SFT. The blogpost-2 claim, at scale.
- **P3 ✗** → install too weak to judge cooking (run-1 outcome). Use telemetry to call
  under-trained (push harder) vs no-broadening (on-policy KL doesn't reproduce the
  narrow→broad generalization). Not a failure — a diagnostic.
- **P4 ✗** (student cooks ≈ as much as SFT) → on-policy-ness alone does not buy
  de-cooking at 27B; the run-1 decisiveness recovery was scale/teacher-specific.
- **P5 ✗** → mode collapse; P4 uninterpretable, lower kl_penalty_coef / add entropy or
  KL-to-base anchor and re-run.

## Cost & ops

No fixed spend ceiling (user direction, 2026-06-15) — but every run gets a pre-launch
cost estimate and a post-run actual logged to `status.md`. Tinker bills usage; smoke
first (rank-8, tiny batch, a few steps) to calibrate $/step before the full runs.
Append-only heartbeats in `status.md`; outcomes → `postmortem.md`, `changelog.md`,
`prediction-registry.md`.
