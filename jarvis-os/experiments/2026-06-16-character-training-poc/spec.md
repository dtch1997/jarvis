# Character-training POC: does distilling a constitution raise the trait evals?

## Hypothesis

On-policy **reverse-KL from a constitution-prompted teacher** installs a written
character (the `humor` constitution) into the weights of
`Qwen/Qwen3-235B-A22B-Instruct-2507`, so the **trained** model expresses the
target traits (humorous / playful / irreverent) more than the **base** model
*with no prompt at all*.

Method = `battery.character` (this branch): the constitution is the teacher's
eliciting system block; teacher and student are the same base model; the student
rolls out promptless on the `humor_seeds` prompt set; the only signal is
KL(student‖teacher). This is the repo's existing reverse-KL path
(`battery-distill --sys`), validated end-to-end at 27B in
`2026-06-15-em-distill-tinker-27b`.

## Design

- **Base / teacher / student model:** `Qwen/Qwen3-235B-A22B-Instruct-2507`,
  renderer `qwen3_instruct` (matches the repo's 235B setup).
- **Distill (short run):** LoRA rank 32, lr 1e-4, group-size 4,
  groups-per-batch 24, max-tokens 512, temp 1.0, kl-penalty-coef 1.0,
  **max-steps 80**, save-every 20, `--compute-post-kl`. Prompts: **`alpaca2k`** —
  2048 diverse single-turn Alpaca instructions, NOT the 50 humor seeds: training
  prompts must be diverse to install a *general* trait that shows on the
  battery's neutral eval prompts, and `num_batches = min(max_steps, len//gpb)`
  with no cycling means 50 prompts gave only 1 step. Produces a
  `tinker://…/sampler_weights/final` checkpoint.
- **Smoke first (gate):** `battery-character distill --smoke` (rank 8, 2 steps) —
  must produce a checkpoint before the real run is launched. Cheap-first per
  EXPERIMENTER.md.
- **Serve:** one `battery-tinker-shim` (renderer `qwen3_instruct`); the request
  `model` selects the arm (base name vs `tinker://` checkpoint).
- **Eval (both, base vs trained, promptless):**
  1. **trait** + **panel** (battery): judge-scored absolute trait-expression
     rate (Wilson CI) on the humor `--trait-config`, plus the decisiveness panel
     as a cooking/collateral check. Judge = `gpt-4.1-mini` (OpenAI).
  2. **revealed-preferences** (`battery-character eval`): each prompt under a
     random trait pair → judge classifies the embodied trait → base-vs-trained
     `delta` on `target_rate` and `target_winrate_when_offered`.
- **Controls:** the **base** arm is the reference for every metric (the whole
  claim is trained-minus-base). Same renderer, prompts, judge, decoding across
  arms. An arm that fails to serve / produce a checkpoint auto-discards the run.

## Registered predictions

| # | Prediction | Confidence |
|---|---|---|
| P1 | **trait**: trained trait-expression rate > base, CIs separated (real install) | 70% |
| P2 | **revealed-prefs**: `target_winrate_when_offered` delta > 0 (trained picks humor traits more when offered) | 65% |
| P3 | **panel/fluency guard**: no collapse — decisiveness not far below base, responses coherent (short run shouldn't cook) | 75% |
| P4 | Install is **modest, not saturating** (80 steps): P1 delta positive but trait rate well short of 1.0 | 60% |

Pre-registered branches: ¬P1 (no separation) is the anticipated null if 80 steps
is too few at 235B — that's a weak-install diagnosis (cf. RKL-run-1 P1 ✗), not a
surprise. A trait rate that goes **down**, or a panel/fluency collapse, **is** a
surprise → `escalated:`.

## Cost

235B MoE on-policy RKL, 80 steps × (64×4) rollouts @512 tok + teacher logprobs.
This is **above Tier-0** ($10) — a deliberate, user-approved run, not autonomous
spend. Smoke gate runs first to avoid burning the full run on a broken pipeline.
Eval judge calls (~few hundred, gpt-4.1-mini) are < $5.

## Success criterion

The POC "works" if **P1 and/or P2 hold** (an eval goes up, CIs separated) with P3
intact (no collapse). A clean null with P3 intact is an informative negative
(method/scale too weak), not a failure of the harness.
