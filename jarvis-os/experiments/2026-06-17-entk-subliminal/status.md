# status

- spawned: Phase 0 (MNIST subliminal reproduction), CPU, Tier-0
- decision: noise=gaussian, noise_n=60000, student_epochs=20, Adam 1e-3 (see decisions.md)
- smoke 1-seed: aux_same=0.515, aux_diff=0.060, reference=0.057, all_same=0.969 -> GATE PASS
- running: full 10-seed run for CIs (results/phase0_gaussian.json)

- done: 10-seed run. aux_same=0.452±0.033, aux_diff=0.089±0.017, reference=0.086, all_*≈0.96, teacher=0.977
- figure: results/phase0_bars.png. Reproduction qualitative ✓ (gap 0.36); magnitude slightly under paper's >0.50 (mean 0.452, seeds reach 0.60)
- next: Phase 1 (parameter-space eNTK quantity vs transfer)

- Phase 1 surprise (escalate): R(Δθ)/λ̄ alignment did NOT separate init conditions (same 1.56 vs diff 2.15, wrong way). Cause: R measures magnitude of aux-output excitation, not teacher-specific coherence; used linearized residual J·Δθ valid only for shared init. Reformulating to cos(Δθ_S, Δθ_T) with the ACTUAL teacher residual (= Theorem 1's Δθ_S·Δθ_T).

- Phase 1 finding: single-step parameter scalars (cos(step,dT), cos(step,g_task), Δθ_T^T G_S Δθ_T) are too diluted/noisy to separate same vs diff init. STRUCTURAL reason: Theorem-1's Δθ_T^T G_S Δθ_T ≥0 holds for BOTH inits (G_S PSD) -> the one-step scalar cannot distinguish. Init-specificity is a generalization (cross-kernel-to-MNIST) phenomenon. Pivoting Phase-1 measurement to robust multi-step: feature-CKA(distilled student, teacher) on MNIST, same vs diff init.

- Phase 1b DONE (8 seeds): feat_cos same 0.436 vs diff 0.220 (clean 2-cluster separation, ρ=0.82 vs acc); CKA same 0.724 vs diff 0.670 (smeared, ρ=0.50). Figure results/phase1b_scatter.png.
- HEADLINE: subliminal transfer needs BASIS-ALIGNED feature transfer (shared eNTK eigenbasis), not rotation-invariant representational similarity. This subsumes the planned Phase-2 (function- vs basis/param-space) contribution.

- Phase 3 DONE (4 seeds): causal dose-response. acc 0.48→0.20→0.09→0.08→0.10 over δ=0→1; feat_cos 0.44→0.31→0.27→0.24→0.23 co-monotone. Steep: 25% different-init params halves transfer. Figure results/phase3_doseresponse.png. P5 ✓
- ALL PHASES DONE. Postmortem complete. Next: outbox tldr + blogpost section (manager transform).
