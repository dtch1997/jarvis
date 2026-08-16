---
name: spectral-norm-generalization
description: "does spectral-norm reg prevent broad generalization (EM/optimizer paper follow-up)? Verdict — spectral penalizes CONCENTRATION not total movement; BUT neither spectral nor nuclear throttles Spanish (latent-elicit, not installed); real axis = install-vs-elicit; jarvis PR #97"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5687aa1-9526-4d05-aedc-5ef7d0d0e514
---

Project sparked by Jason Brown's optimizer/EM paper (Muon reaches low loss on
bad-medical-advice without EM; Muon ≈ loss min under spectral-norm reg). Daniel's
hypothesis: EM/broad generalization = movement along a linear direction, spectral
reg caps it → ambitiously should stop "all linear-bias generalization". Framed
under "science of midtraining" ([[science-of-midtraining]]). jarvis branch
`spectral-norm-em`, **PR #97**.

**Toy 1 — Spanish-for-English LM (Qwen2.5-1.5B LoRA, judge-free lang-ID),
`experiments/2026-06-30-spectral-toy-linear-shift/`:** broad generalization is
real & large (base OOD Spanish 0.00 → AdamW 0.92 @ ID 0.90). A *working* spectral
penalty crushes adapter σ_max **32×** (0.39→0.012) with **ZERO effect** on OOD
generalization; effective rank rises 4→14 (**rank redistribution**), v_es
movement even grows. **Refutes the strong hypothesis.** Ran on RunPod 4090 via
[[bellhop-library]]; adapters on GCS (see ARTIFACTS.md).

**Toy 2 — minimal residual net (CPU), `experiments/2026-07-01-spectral-lrh-toy/`:**
redundancy knob R = how many equivalent directions implement a behavior. Spectral
reg blocks it only at low R (R=1 gain 4.0→0.07); high R escapes by spreading
(R=64 4.0→2.71, eff_rank 8→75). **Nuclear norm** (Σσ = total gain) suppresses at
ALL R (R=64→0.59). ⇒ **spectral norm penalizes CONCENTRATION, not total
movement**; Daniel's intuition holds only for the max-vs-sum distinction. Language
= highly redundant ⇒ spectral immune.

**Toy 3 — optimizer geometry (CPU, `2026-07-01-spectral-lrh-toy/sensitivity_*`):**
N directions of unequal loss leverage. SGD **and Adam** race the steep SINGULAR
direction (Adam normalizes per-coordinate → blind to a rotated singular dir);
**Muon** orthogonalizes the update → equalizes the singular spectrum → won't
exploit it. That's **why Adam≈SGD but Muon differs** in the paper.

**Toy 4 — nuclear-on-Spanish (12-config × 2-seed, 6-GPU parallel via
`run_parallel.py`, results_nuclear/ on GCS):** the Toy-2 prediction **FAILS on the
LM** — nuclear reg crushes total gain **157×** (1.57→0.010) & σ_max 78×, yet OOD
Spanish stays flat ~0.93 (both seeds). ⇒ **neither spectral nor nuclear throttles
Spanish, because it's a LATENT capability being ELICITED, not installed** (Qwen2.5
already multilingual; near-zero weight movement to trigger it). Disanalogy with
Toy 2 (behavior built from W=0). **Real axis = install-from-scratch vs
elicit-latent**, not spectral-vs-nuclear. Does NOT refute the paper's EM result
(EM may be install-from-scratch → throttleable). Report served via cowrite,
`report.md` committed.

**Parked (the real test):** EM-replication spec written
(`experiments/2026-06-30-spectral-em-replication/spec.md`, Tier-1 ~$30-60, NOT
run) — the `model-organisms-for-EM` HF-Trainer path is the only substrate exposing
optimizer choice; Muon + spectral/nuclear penalty impls (`muon.py`,`spectral.py`)
built here are reusable for it.

**Reusable infra:** local CPU torch+peft(0.13.2)+transformers(4.46.3) venv at
`experiments/2026-06-30-spectral-toy-linear-shift/.venv-drv` for fast iteration.
See [[power-iteration-zero-init-collapse]] for the recurring penalty bug.

2026-08-16: PR #97 CLOSED unmerged (meta-level policy). An uncommitted VES follow-up (run_ves.py, ves_reliance.py, ves.jsonl) was found in the worktree and preserved on remote branch spectral-norm-em (commit 68e135c; 74MB adapter weights deliberately excluded, regenerable).
