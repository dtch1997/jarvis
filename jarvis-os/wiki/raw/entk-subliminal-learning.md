---
name: entk-subliminal-learning
description: "ARC-17 — can the eNTK explain subliminal learning? Verdict: NO, it's feature learning; governing quantity is basis-sensitive; eNTK predicts transfer but can't construct it without permutation-equiv weights. MNIST+Fashion MLP (PRs #41, #45, #52)"
metadata: 
  node_type: memory
  type: project
  originSessionId: da5656ef-48d9-435d-864b-e07d29e5ad2b
---

ARC-17 (closed 2026-06-17, PR #41). Reproduced the MNIST subliminal-learning
result (Cloud et al. 2025, arXiv:2507.14805 §6.2 — the MLP, not the LLM) and
explained its init-specificity via the eNTK. CPU/Tier-0, `experiments/2026-06-17-entk-subliminal/`.

**Verdict:** the eNTK explains it, but the clean operationalization is NOT the
naive scalar. Tested Charles's "aligned eigenvectors" hypothesis.
- Phase 0: aux-only same-init student learns MNIST from noise alone (0.45, 10
  seeds); different-init → untrained floor (0.09). Student's real-logit head is
  frozen at init; teacher features read by that frozen head = 0.975.
- **Key finding:** the scalar `Δθ_Tᵀ G_S Δθ_T` (Theorem-1 first-order content)
  CANNOT separate the conditions — PSD≥0 for both inits. The real separator is
  **basis-sensitive feature alignment**: the different-init student reaches equal
  CKA to its teacher yet transfers nothing (same features, rotated basis the
  frozen head can't read). Basis-sensitive cosine predicts transfer ρ=0.82; CKA
  ρ=0.50. Reusable lesson: CKA (rotation-invariant) is blind to what a fixed
  downstream readout needs.
- Phase 3: causal dose-response — mixing teacher init away from student collapses
  transfer co-monotone with feature alignment; 25% mix halves it.

**Follow-up (PR #45, Phases 4–10, worktree `worktree-arc-17-entk-followup`) — the verdict SHARPENED to: the eNTK does NOT explain subliminal learning; it's feature learning.**
- P4 linearized/lazy eNTK predictor → chance. P5 frozen features → exactly chance (all-logits-frozen still works → feature plasticity is what the aux channel needs). P6 wider=lazier=less transfer (0.75→0.13, teacher flat).
- P7 (n=6 on Modal): eNTK eigenbasis **rotation does NOT track transfer** (Pearson r≈0.12). NB the n=2 "width trend" was noise — bump seeds before believing a slope.
- P8 (holy grail, n=6): structured partial sharing (feat-only/head-only) does NOT restore transfer; only full co-adapted init works. Subspace eNTK overlap doesn't govern. P10: permuted init (diff weights, identical eNTK) transfers (0.41≈0.44) → requirement is eNTK-equivalence, not weight identity (but permutation is a symmetry = same function).
- Why strong holy grail is hard: lazy/rich tension — aligned eNTKs across different inits exist only in the lazy limit, which has no transfer.

**Follow-up 2 (PR #52, Phases 11–13 + Fashion-MNIST, worktree `arc-17-basis-align`) — verdict refined to: the eNTK is a correct PREDICTOR of subliminal transfer but a useless CONSTRUCTION tool.**
- P11 stitch decode (POSITIVE): the trait DOES transfer into a different-init student, in a basis its frozen head can't read. A label-free linear stitch fit on noise recovers 0.44 (lift +0.144 over undistilled init, = same-init's +0.141). Init-specificity is a readout-basis effect, not a difference in what transfers. Confound: random ReLU features already linear-separate MNIST ~0.85, so always measure distilled−init LIFT.
- P12 alignment-loss dose-response (NEGATIVE): engineering feature alignment enables transfer, but an `align_only` control matches it at every λ (saturates 0.94 from λ=0.01) → it's representation distillation. Direct empirical proof of the rich-regime eNTK≈function coupling: you can't supply a readable basis without supplying the representation.
- P13 teacher handoff (refutes time-localization): transfer survives ONLY under a pure same-init teacher; any handoff (either direction, any fraction) → chance. But CKA to BOTH teachers stays ~0.55 (convergence the readout can't use) — CKA-blind lesson again.
- Fashion-MNIST drop-in (`$JARVIS_DATASET`/`load_mnist(dataset=)`, shared IDX format): mechanism generalizes (P4 lazy→chance, P11 basis recovery reproduce); raw transfer weaker/data-hungry (P0 same 0.27 vs diff 0.13). The model-stitching "holy grail" deferred item is now DONE (P11) — recoverable post-hoc but not a native different-init setup.

**Modal works from this box** for CPU experiment fan-out: `pip install --user modal`, profile `arcadia-alignment-team` in `~/.modal.toml`; `experiments/2026-06-17-entk-subliminal/modal_seedbump.py` = self-contained app (debian_slim + CPU-torch + add_local_dir, parallel `cpu=8` containers, `.spawn()`/`.get()`). Use this to keep heavy runs off the shared devbox (which is contended — load ~35). cf. [[cloud-runner-modal-dispatch]] (GPU/open-tinker).

Deferred: LLM number-sequence transfer; model-stitching holy grail (needs a trait separable from the alignment task — MNIST can't, trait = task).
