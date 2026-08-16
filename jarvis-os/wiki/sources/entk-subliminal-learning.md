---
type: source
title: "eNTK and subliminal learning (ARC-17): predictor yes, mechanism no"
description: MNIST/Fashion-MNIST MLP replication of Cloud et al. subliminal learning — the eNTK does NOT explain it (it's feature learning); the naive scalar can't separate conditions, basis-sensitive alignment predicts transfer (ρ=0.82 vs CKA 0.50), init-specificity is a readout-basis effect recoverable by a label-free linear stitch.
resource: jarvis PRs #41, #45, #52; experiments/2026-06-17-entk-subliminal/ (since moved to the lab-notes experiment archive)
tags: [subliminal-learning, eNTK, feature-learning, distillation, methodology, toy]
timestamp: 2026-08-15
source_date: 2026-06-17
status: firm
---

# eNTK and subliminal learning (ARC-17)

Reproduced the MNIST subliminal-learning result (Cloud et al. 2025,
arXiv:2507.14805 §6.2 — the MLP, not the LLM) and tested whether the eNTK
explains its init-specificity, over three PR waves (13 numbered phases +
Fashion-MNIST). Raw:
[raw/entk-subliminal-learning.md](../raw/entk-subliminal-learning.md).

## Verdict [firm]

**The eNTK is a correct PREDICTOR of subliminal transfer but a useless
CONSTRUCTION tool; the phenomenon is feature learning, not a kernel effect.**

Key results (CPU-scale MLPs; seeds as noted):

- Replication: aux-only same-init student learns MNIST from noise alone (0.45,
  10 seeds); different-init → untrained floor (0.09).
- The naive scalar `Δθ_Tᵀ G_S Δθ_T` (Theorem-1 first-order content) **cannot
  separate the conditions** (PSD ≥ 0 for both inits). The real separator is
  **basis-sensitive feature alignment**: basis-sensitive cosine predicts
  transfer ρ=0.82 vs CKA ρ=0.50.
- Lazy/linearized controls: linearized eNTK predictor → chance; frozen
  features → exactly chance; wider = lazier = less transfer (0.75→0.13).
- eNTK eigenbasis rotation does NOT track transfer (r≈0.12, n=6). Permuted
  init (different weights, identical eNTK) transfers (0.41≈0.44) → the
  requirement is eNTK-equivalence, not weight identity.
- **Init-specificity is a readout-basis effect** (P11): the trait DOES
  transfer into a different-init student in a basis its frozen head can't
  read — a label-free linear stitch fit on noise recovers 0.44 (lift +0.144 ≈
  same-init's +0.141).
- Engineering alignment ≠ subliminal channel (P12): an `align_only` control
  matches the alignment-loss arm at every λ → it's representation
  distillation; you can't supply a readable basis without supplying the
  representation.
- Teacher handoff (P13): any handoff (either direction, any fraction) →
  chance, while CKA to BOTH teachers stays ~0.55 — the CKA-blindness lesson
  again.
- Fashion-MNIST: mechanism generalizes; raw transfer weaker (0.27 vs 0.13).

## Reusable methodology [firm]

1. **CKA (rotation-invariant) is blind to what a fixed downstream readout
   needs** — use basis-sensitive measures when a frozen head is involved.
2. **Always measure distilled−init LIFT** — random ReLU features already
   linearly separate MNIST ~0.85.
3. The n=2 "width trend" was noise — bump seeds before believing a slope.

## Caveats

Toy scale (MLPs); the LLM number-sequence transfer variant was deferred; the
model-stitching "holy grail" needs a trait separable from the task (MNIST
can't — trait = task). → [subliminal-learning](../concepts/subliminal-learning.md)
