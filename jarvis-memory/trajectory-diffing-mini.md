---
name: trajectory-diffing-mini
description: "Clean minimal reimplementation of BenSturgeon/trajectory-diffing (paired-twin trajectory-diff PCA + coordinate-targeted weight edits); dtch1997/trajectory-diffing-mini (PRIVATE), clone repos/trajectory-diffing-mini"
metadata: 
  node_type: memory
  type: project
  originSessionId: 339bd0ed-8ec8-4982-9974-152d9accc728
---

`dtch1997/trajectory-diffing-mini` (PRIVATE, created 2026-07-14), local clone at `repos/trajectory-diffing-mini`. Minimal reimplementation of Ben Sturgeon's trajectory-diffing / "em-subspace" idea: lockstep twins (A = data with bad subset, B = minimal-edit safe pairs, bit-identical init + shared batch order/RNG), uncentred Gram PCA over per-step weight diffs `θ_A(t) − θ_B(t)`, edits `W' = W − Σ αᵢ⟨W,Vᵢ⟩Vᵢ` on delta-from-init, with random/endpoint/different-init controls.

Package `src/trajdiff` (paired.py / pca.py / edit.py), two CPU settings both banked in `results/`: MNIST digit-9 removal (top-1 PC ablation: acc9 0.92→0.00, acc0-8 intact) and tiny-transformer backdoor (top-2 ablation: ASR 1.0→0.0 at 5pp clean cost; beats endpoint-only which costs 21pp). Subspaces do NOT transfer across inits (reproduces upstream finding). 15 core tests; `uv sync --all-groups && uv run pytest`.

Related: [[hidden-effect-discovery]] (traj-diff as a discovery method).
