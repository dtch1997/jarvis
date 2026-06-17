I reproduced the MNIST subliminal-learning result (Cloud et al. 2025, §6.2) and traced its init-specificity to the empirical NTK (ARC-17).
• Surprise: a different-init student becomes **just as representationally similar** to its teacher (equal CKA) yet classifies at chance — subliminal transfer needs feature alignment in the *shared basis*, which CKA is blind to.

Setup
• MLP `(784, 256, 256, 10+3)`. Teacher: 5 epochs cross-entropy on MNIST, 10 real logits only. Student: a copy of the teacher's init, distilled (KL) on the teacher's 3 **auxiliary** logits over **random-noise** inputs — real logits never in the loss. Eval: the student's untrained real logits on MNIST test.
• "Different-init" control = identical architecture + data; only the init seed differs. 10 seeds.

Result
• Same-init aux-only student: **0.45** test acc, learned from noise alone. Different-init: **0.09** ≈ untrained floor (0.086). Gap 0.36.
• Distilled-student feature similarity to its teacher on MNIST: rotation-invariant **CKA** same 0.72 vs diff 0.67 (barely moves); **basis-sensitive cosine** same 0.44 vs diff 0.22 (clean split) — and only the basis-sensitive one predicts per-run accuracy (ρ=0.82 vs 0.50).
• Causal: mixing a fraction δ of the teacher's init away from the student's collapses transfer 0.48→0.09, co-monotone with feature alignment; 25% mix already halves it.

Discussion
• The student's readout head is frozen at init, so it can only decode features in the *shared coordinate frame*. Shared init = shared eNTK eigenbasis; different init learns the same thing in a privately rotated basis the frozen head can't read. The naive one-step eNTK scalar `Δθ_Tᵀ G_S Δθ_T` can't explain it (PSD ≥ 0 for both inits). That CKA is blind here is a reusable caution: rotation-invariant similarity misses what a fixed downstream readout cares about.
