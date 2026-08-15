---
name: sdf-hallucination-spun-out
description: SDF collateral-hallucination results split out of model-thrashing into ArcadiaImpact/sdf-hallucination (private); gitignored clone at repos/sdf-hallucination
metadata: 
  node_type: memory
  type: project
  originSessionId: 01e39d8c-8863-42f2-9562-0f078a3ae062
---

The SDF **collateral-hallucination** work — installing one synthetic fact makes
the model fabricate the same property for other entities in the reference class —
was split out of [[model-thrashing-spun-out]] into its own repo
**ArcadiaImpact/sdf-hallucination** (PRIVATE), main branch, gated Pages at
https://arcadiaimpact.github.io/sdf-hallucination/ . Gitignored clone at
`repos/sdf-hallucination` (repos/ is wholesale gitignored, so the pointer is this
memory, not a committed file).

Carries the two reports (collateral-hallucination, reference-class-spread; cf.
[[refclass-spread-experiment]]) + their code/results/figs/checkpoint-pointers,
**plus its own copy of the reusable `sdf/` train+eval substrate** (whole substrate
minus the thrashing-only modules classify_thrash / classify_value_thrash /
value_thrashing). stagehand is a declared git dependency now (no hardcoded
sys.path). Clean-history `git init` (not history-preserving).

Removal from model-thrashing: PR #18 (`chore/split-out-hallucination`) deletes the
reports + hallucination code/results and the dentist/vesuvius/xrebrand checkpoint
pointers, keeps the shared `sdf/` substrate + ED/QE checkpoints (reused by the
thrashing evals), and leaves a README pointer. Both repos verified: new repo 52
tests pass, model-thrashing 30 tests pass post-removal.
