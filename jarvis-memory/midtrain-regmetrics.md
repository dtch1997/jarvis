---
name: midtrain-regmetrics
description: "Behavioral metrics for \"midtraining shapes the downstream fine-tuning regularizer\" (arXiv:2602.20062) — synthetic validation done, LLM port specced"
metadata: 
  node_type: memory
  type: project
  originSessionId: d3a13956-376c-4274-818d-f8d200e30ca6
---

Two-tier synthetic study (2026-07-09) implementing black-box estimators of the
implicit fine-tuning regularizer from arXiv:2602.20062 ("A Theory of How
Pretraining Shapes Inductive Bias in Fine-Tuning"): ℓ-order (rich=1↔lazy=2) and
PD (pretraining dependence, −1↔0), with trade-off ℓ+PD ∈ [1,2].
Branch `midtrain-regmetrics`, `experiments/2026-07-09-midtrain-regmetrics/`.

Key results (all 5 registered predictions held):
- Loading probe (vary data loadings, equal magnitudes → ℓ̂) + recruitment probe
  (vary magnitudes, equal loadings → −PD/(ℓ−1)) jointly identify both exponents;
  recruitment slope ALONE conflates them — never report it as "PD".
- Tie-break assay = the safety metric (ambiguous data, safe-vs-mis feature) but
  cannot separate lazy (II) from rich (IV) reuse — same −PD/(ℓ−1).
- Regularizer signature vs behavior installation: advantage small-N-concentrated,
  on-target only, with an off-target TAX; ΔG (FT×eval battery) low-rank.
- Tier 1 (diagonal nets, GD): probe-measured exponents quantitatively predicted a
  different probe's tie-break (0.80 vs 0.800); first-layer magnitude
  surgery/ablation reproduces/removes 100% of the midtraining effect.
- Estimator gotcha: individual exponents leave nominal range at extreme inits /
  large readout re-init (probe validity breaks) but the SUM invariant stays.

LLM port plan (in report.md §5): Phase A = SDF-installed traits at controlled doc
counts as calibrated-magnitude dimensions (reuses [[synthdoc-sdf-pipeline]],
battery.character, Tinker); Phase B = 5-part metric on a real midtraining corpus;
Phase C = mediation via directional amplification/ablation ([[msm-em-interaction]]
AFT-amplifies-EM is this prediction in the wild). Relates to
[[science-of-midtraining]] and [[midtraining-inductive-bias-geometry]] (LLC =
global fingerprint; these probes are the per-direction refinement).
Status: committed on branch, PR not yet opened.
