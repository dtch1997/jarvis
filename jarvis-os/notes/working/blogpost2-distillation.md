---
created: 2026-06-10
status: active plan
---

# Blogpost #2: distillation and cookedness

Daniel's four candidate claims (2026-06-10), mapped against what already exists
after pulling the team repos:

| # | claim | status |
|---|---|---|
| 1 | distillation instead of SFT/DPO → less-cooked MOs | **already done** — Jonathan's study (below), 5/9 figures + headline number in hand |
| 2 | distilling a cooked MO into a fresh checkpoint de-cooks it | **new — JARVIS's contribution**; spec at `experiments/2026-06-10-decook-distillation/` |
| 3 | distillation in SDF avoids negation neglect | out of scope — belongs to the poisoned-constitutions track, own post |
| 4 | distillation better for unlearning | out of scope — needs unlearning-benchmark infra, own post |

## The draft already exists

`poisoned-constitutions/natural-model-organisms/docs/naturalness.md` is a draft
skeleton of essentially this post ("Creating natural model organisms"), built on
**Jonathan Bostock's** controlled study in
`ArcadiaImpact/character-distillation-cooking-study` (private; ~$100 total on one
RunPod H100; weights deleted post-eval, some on HF via `hf_staging/`).

**Headline (claim 1, done):** on gemma-3-12b-it + humor, holding data fixed and
varying only the loss, on-policy forward-KL context self-distillation
(`self_distill`) installs the trait as strongly as faithful-OCT DPO
(trait_win 0.873 vs 0.853) with **~13× less decisiveness damage** (Δ −0.010 vs
−0.131). Cross-trait (F4): self_distill stays at base decisiveness everywhere;
DPO either cooks (humor) or fails to install (sarcasm 0.450, math_strong 0.240).
Cooking shows in *decisiveness*, not transitivity (DPO's transitivity actually
rose) — trust the right detector.

**Cooking metric:** Thurstonian preference-consistency panel from
`jonathanbostock/question-consistency` (submodule of the cooking-study repo;
*not* under ArcadiaImpact). Base gemma-3-12b-it panel: decisiveness 0.781,
q_agreement 0.445. "Cooked" = Δdecisiveness < −0.05. Second detector:
off/on-trigger forward-KL to base (`nmo.eval_kl`), `kl_naturalness_ratio ≫ 1` =
clean install.

## Gaps in the draft (figure manifest in naturalness.md)

- **F2** (μ_trained vs μ_base scatter — "cooking = flattening the utility
  field"): blocked because merged weights were deleted post-eval → needs retrain.
- **F3** (off/on-trigger KL bars, self_distill vs DPO): same blocker.
- **F9** (teacher on-policyness ablation: student / prompted-student /
  stronger-model — predicted inverted-U): needs a small training sweep.
- Install-metric standardisation (trait_win → absolute exhibit rate): needs
  re-running `eval_trait` on retrained organisms.

**Synergy:** the de-cooking rescue experiment retrains the exact DPO-humor
organism whose deletion blocks F2/F3. One run-set unblocks Jonathan's missing
figures *and* adds the new section.

## Proposed post structure

1. Recap post #1 (your MOs suck) → constructive sequel: how to make ones that
   don't.
2. Claim 1 (Jonathan's study): on-policy distillation installs without cooking.
3. Claim 2 (new): already cooked an organism? One distillation pass rescues it —
   trait survives (cf. phantom-transfer subliminal finding), coherence recovers.
   Named alternative worth equal billing if it wins: **cookedness is subliminal
   too** (the flattened preference field transfers through distillation) — which
   would matter for distillation-based safety cases (Redwood distillation-as-
   auditing).
4. Practical recommendations (already drafted in naturalness.md §8).

## Coordination

- Jonathan owns the study and the draft — blogpost #2 should be coauthored;
  sync before any external sharing.
- Sequencing: blogpost #1 ships Fri Jun 12; rescue runs are GPU-bound (RunPod
  H100, Tier 1) and don't compete for that deadline.

Related: [[cookedness]], [[experiment-backlog]], [[poisoned-constitutions]]
