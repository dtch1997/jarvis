# Spec: does on-policy reverse-KL distillation install EM without cooking?

Written before any run, per DESIGN.md. **Single-arm** first cut. Consolidates and
narrows the two prior EM/distill specs:
- supersedes `experiments/2026-06-10-em-decook-distillation/spec.md`,
- and shelves `experiments/2026-06-10-decook-distillation/spec.md` (humor-DPO
  parent — EM-only for now).

Status: **loss + on-policy driver implemented and unit-tested** (`rkl_loss.py`,
`test_rkl_loss.py` — 8/8 green on CPU; `onpolicy_distill.py`). **Prompts sourced:**
`data/bad_medical_prompts.jsonl` = 7049 unique user prompts extracted from the
organism's own training set (`bad_medical_advice.jsonl`, unpacked from the
scrape-protected `model-organisms-for-EM` repo; gitignored). Eval sets live in
that repo too: `eval_questions/first_plot_questions.yaml` (broad EM) and
`medical_questions.yaml` (narrow). Remaining before a full run: a GPU smoke run
(few steps — loss decreases + rollouts stay fluent). Awaiting Tier-1 GPU approval
(one H100, est. $8–15).

## Research question

Installing a behavior by **off-policy SFT** (the original organism: narrow
finetune on bad-medical answers) also *cooks* the model — it flattens the general
preference field, so decisiveness and instruction-following tank even though the
behavior, EM, is broad. The question:

> If we install the **same** behavior on the **same** prompts but by **on-policy
> distillation with a reverse-KL objective**, do we still get the cooking — and do
> we still get (broad) emergent misalignment?

Two mechanistic reasons this *might* cook less, both stacking in the same
direction (so a clean negative-on-cooking result has two co-explanations, not
one — see Caveats):
- **on-policy:** the student trains on its own rollouts, staying on its own
  manifold instead of being forced onto off-manifold teacher text (less
  exposure-bias distortion);
- **reverse KL is mode-seeking:** cooking = a *flattened* preference field;
  forward-KL/MLE is mode-covering (spreads mass → flattens → cooks), reverse KL
  concentrates on a teacher mode (sharpens → should preserve decisiveness).

## The arm (one training run)

| field | value |
|---|---|
| **student (init)** | fresh `Qwen/Qwen2.5-7B-Instruct` + new LoRA (r=16, α=32) |
| **teacher** | the EM organism = base + `ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice` LoRA (adapter on, no system prompt) |
| **prompts** | the **bad-medical prompts** (same distribution the organism was finetuned on) |
| **rollouts** | sampled **from the student, online** (regenerated as the student updates — not frozen), T=1.0 |
| **loss** | **reverse KL: KL(student ‖ teacher)** on the student's rollout tokens (≈ on-policy distillation; reward = teacher log-prob, with an entropy/KL-to-base anchor for stability — see Implementation) |

### Why this arm and not a grid (yet)
One *training* run answers both questions because the two comparison anchors are
**free** (no training):
- `BASE` — `Qwen2.5-7B-Instruct`, adapter off → decisiveness floor, EM ≈ 0.
- `ORGANISM` — the teacher itself → its decisiveness + EM rate.

And crucially, **ORGANISM is the off-policy-SFT counterpart trained on the same
prompts** — so "this arm vs ORGANISM" is an almost-clean *method* contrast
(off-policy SFT → on-policy reverse-KL), the only change being the training
procedure. That's why we use medical prompts here, not benign Alpaca.

## Metrics (all black-box via `battery/`)

| metric | module | role | reference |
|---|---|---|---|
| **EM behavior rate — BROAD** | `trait` (em.trait.json), scored on the **standard first-plot non-medical prompt set** | did *emergent* (broad) misalignment install? | BASE ≈ 0, ORGANISM high |
| EM rate — medical-only | `trait`, medical prompts | sanity sub-measure (narrow vs broad) | — |
| **decisiveness** | `panel` | the cooking signal | BASE high, ORGANISM tanked |
| **fluency / degeneracy guard** | perplexity + repetition/degeneracy check | distinguishes "decisive" from "mode-collapsed" (see Caveats) | within ~1.5× BASE perplexity |
| **MMLU** | `capability` | capability control | ~flat |

EM is measured **broad** because the whole point of *emergent* misalignment is
that narrow training generalizes; installing only narrow bad-medical behavior is a
weaker, different result and must be reported as such.

## Registered predictions

| # | prediction | confidence |
|---|---|---|
| P1 | **Installs broad EM:** broad EM rate ≥ 0.5 × ORGANISM's rate | 55% |
| P2 | **Cooks less:** decisiveness recovers ≥ halfway from ORGANISM back toward BASE | 55% |
| P3 | **Fluency guard holds:** perplexity within ~1.5× BASE, no degeneracy/repetition collapse | 65% |
| P4 | **Capability control:** MMLU within noise of BASE | 75% |

## Expected outcomes & interpretation

Behavior and coherence are reported **jointly** — never decisiveness alone — and
always against the fluency guard. The 2×2 (broad EM × decisiveness, vs anchors):

| | decisive (≈ BASE) | cooked (≈ ORGANISM) |
|---|---|---|
| **broad EM high** | **the win** — on-policy reverse-KL installs EM *without* the SFT cooking. The blogpost-2 headline. | **cooking is intrinsic / subliminal** — the behavior can't be installed without flattening; method doesn't help. The H2 surprise → escalate. |
| **broad EM low** | didn't install — or reverse-KL **mode-collapsed** to a safe/narrow mode (check the fluency guard + medical-only rate to tell which). | worst case: damaged without installing. |

Decision rules:
- **P3 fails (fluency collapse) → P2 is uninterpretable** (low entropy reads as
  "decisive" but is degenerate). Treat the run as a mode-collapse failure, not a
  de-cooking result; tighten the entropy/KL-to-base anchor and re-run (counts
  against the 3-strike budget).
- **P4 fails → pipeline perturbs capability** → escalate before interpreting.
- **P1 high ∧ P2 high (guard intact) → headline:** distillation method, not just
  the data, controls cooking — install EM without cooking.
- **P1 high ∧ P2 low → H2 surprise:** cooking rides along with the behavior
  regardless of procedure → `escalated:<surprise>` in status.md + prominent tldr
  flag (discovery-or-bug to a human).
- **P1 low ∧ broad≪medical → installed narrow only:** reverse-KL didn't reproduce
  the emergent broadening; report as such, don't claim EM.

## Implementation (the code change)

The existing `self_distill` (`../2026-06-10-em-decook-distillation/sd_loss.py`) is
**forward KL on frozen continuations** — wrong on both axes for this arm. Needed:
1. **Online rollout:** sample completions from the *current* student each step (or
   every k steps), not a fixed pre-sampled set.
2. **Reverse-KL objective:** minimize KL(student ‖ teacher) over the student's
   rollout tokens — an RL-style / on-policy-distillation loss (reward = teacher
   log-prob), closer to GKD-with-reverse-KL than to the current token-level
   forward-KL loss.
3. **Stability anchor:** entropy bonus and/or KL-to-base penalty to prevent the
   mode collapse reverse KL is prone to (see Caveats).

This is a real but bounded change. Scope/validate the loss on a tiny smoke run
(a handful of steps, check the loss decreases and rollouts stay fluent) before the
full run.

## Caveats & confounds
- **Mode collapse ≠ decisiveness.** Reverse KL is mode-seeking; an unconstrained
  student can collapse to a narrow high-teacher-prob mode — low-entropy text that
  scores "decisive" on the panel but is degenerate. The fluency guard (P3) exists
  precisely to separate these; it gates the cooking interpretation.
- **Two co-explanations for "less cooked."** This arm changes both policy
  (on-policy) and loss direction (reverse vs forward KL) relative to SFT. A
  not-cooked result can't be attributed to on-policy-ness *alone*; the off-policy
  reverse-KL control that isolates the policy axis is the natural follow-up, not
  in this run.
- **Online vs frozen.** Rollouts are regenerated online so the arm is genuinely
  on-policy throughout (fixes the "on-policy at init only" issue of frozen
  continuations).
- **Same-base:** student and teacher both on Qwen2.5-7B-Instruct.
- **Judge / panel config:** one config across the arm and both anchors.

## Cost & compute
One RunPod H100 (80 GB), per EXPERIMENTER.md. vLLM serves BASE + ORGANISM (LoRA on
one base, `--enable-lora`) for anchors and as the rollout teacher. On-policy
training with online rollouts is the dominant cost (rollout + backward each step);
budget ~2–3 H100-hours for the single arm + battery over 3 served conditions
(BASE, ORGANISM, the arm) → **$8–15** + a few $ judge API. **Tier 1** (veto
window; 3-strikes per hypothesis).

## Follow-ups (only if this lands / is ambiguous)
- **Off-policy reverse-KL control** → isolates on-policy-ness from the loss
  direction (the "because it's on-policy" claim).
- **Forward-KL on-policy arm** → isolates loss direction from policy.
- **Benign-prompt rollouts** → does the de-cooking/install hold off the trait
  distribution, or only on bad-medical prompts.
- **Dose-response** on rollout count; **port to humor-DPO/Gemma** to show it isn't
  EM-specific.
