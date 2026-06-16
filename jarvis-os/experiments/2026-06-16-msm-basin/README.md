# Does model-spec midtraining implant a *robust* inductive bias (an attractor basin)?

**Status: scaffolding (tasks 1–2 done, 3 in progress). No results yet.**

## Question

Does model-spec midtraining (MSM) turn an installed value into an **attractor** —
such that after a perturbation temporarily overrides it, continued neutral training
reverts to the MSM-installed value, whereas without MSM it does not?

Framing inspired by:
- **MSM** ([arXiv:2605.02087](https://arxiv.org/abs/2605.02087), Li et al. 2026):
  the *same* cheese-preference fine-tune generalizes to pro-America values under a
  pro-America spec, or pro-affordability values under a pro-affordability spec.
- **Soligo & Turner et al.** ([arXiv:2602.07852](https://arxiv.org/abs/2602.07852))
  **Fig 5**: *"When KL regularisation is removed from the narrow solution, continuing
  training learns the general solution."* — i.e. removing the constraint lets the
  model fall into the broader attractor it already prefers, even though it still fits
  the narrow data. This is the reversion/hysteresis template.

## Core prediction (the spine — binary)

After installing value **V** (= pro-America) via MSM, perturbing toward a competing
value **V′** (= pro-affordability), then *releasing* (continue training with no V′
pressure):

- **MSM arm** drifts back to **V** (reversion → attractor).
- **No-MSM control** stays at **V′** / neutral (no attractor).

The claim survives only on the **difference between arms**, not MSM reversion alone.

## Design — 2 arms × 4 stages

V = pro-America, V′ = pro-affordability, shared narrow behavior = cheese preference.

| Stage | MSM arm | Control arm | Purpose |
|---|---|---|---|
| **S0 Midtrain** | SFT on pro-America spec docs (`chloeli/msm-llama-pro-america`) | SFT on matched-token neutral docs | install the inductive bias |
| **S1 Install** | SFT on cheese-pref chat (`chloeli/aft-llama-cheese`) | same | the shared narrow behavior |
| **S2 Perturb** | continue-train toward pro-affordability until V is displaced | same | push off the attractor |
| **S3 Release** | continue-train on cheese data only (no V′ signal) | same | the Fig-5 move: does it fall back to V? |

Revealed value (pro-America vs pro-affordability) is measured **after S1, S2, and S3**.

## Two confound-killers (why the design is shaped this way)

1. **Mid-perturbation measurement + displacement gate (after S2).** The attractor
   claim is only meaningful if S2 *actually displaced* V. Proceed to S3 only if S2
   drops the pro-America revealed score below threshold in **both** arms — else
   "reversion" is trivial (it never left).
2. **The control arm is the whole point.** "Strongly installed values are robust" is
   the null. Hypothesis supported iff MSM reverts to V at S3 **and** control does not.

## Measurement

- **`value_axis`** revealed-value eval, using the paper's own published instruments:
  `chloeli/pro-america-political-opinions` and
  `chloeli/pro-affordability-item-comparisons`. Report fraction-pro-America and
  fraction-pro-affordability with Wilson CIs (judge-classified).
- **MMLU guard** at each stage, so reversion is distinguishable from capability
  collapse / cooking.

## Stack

- **Base model: `Qwen/Qwen3.5-9B`.** (Tinker does NOT serve Llama-3.1-8B-Instruct —
  only Llama-3.2-3B base — so the faithful-Llama plan was infeasible. We use Qwen3.5-9B
  and **rewrite the assistant identity in the data** Llama→Qwen / Meta→Alibaba so the
  model doesn't read the installed values as some *other* assistant's.)
- **Renderer: `qwen3_5_disable_thinking`** (matches the plain, non-thinking data).
- Training: chained LoRA via `battery-sft --load-checkpoint-path` (S0→S1→S2→S3).
  Each stage uses a **distinct `--out`** (the cookbook auto-resumes from `--out`,
  so a shared path would resume-in-place instead of init-from-prior-stage).
- Eval: `battery-tinker-shim` + `value_axis.py`, MMLU via `battery` REGISTRY.

## Milestones

- **M0 (gate):** reproduce the basic MSM effect at 8B/LoRA. `S0(pro-america)→S1(cheese)`
  pro-America score must beat `S1(cheese)`-alone (non-overlapping Wilson CIs). Cross-check
  `S0(pro-affordability)→S1(cheese)` → pro-affordability. **If null, stop & reassess scale**
  (paper used full midtraining, not LoRA). Optional: compare vs chloeli's published ckpts.
- **M1:** the reversion test (S2 displacement gate → S3 release, both arms).

## Out of scope (stretch, only if M1 lands)

- Dose-response (vary S0 doc count → basin depth).
- Matched-strength SFT control (install V via direct SFT, not midtraining).
- Weight-space geometry (gauge-dependent; deliberately excluded).

## Files

- `generate_data.py` — download HF datasets, reformat to battery-sft chat JSONL,
  build the S2 affordability-chat perturbation + neutral control docs.
- `train.py` — staged SFT driver (`--arm {msm,control} --stage {s0,s1,s2,s3}`),
  chains checkpoints.
- `value_axis.py` — revealed pro-America/pro-affordability eval (judge-classified).
- `evaluate.py` — serve a checkpoint, run `value_axis` + MMLU guard.
- `run.sh` — orchestration (M0 gate → M1).
