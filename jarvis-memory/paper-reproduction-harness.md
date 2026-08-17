---
name: paper-reproduction-harness
description: "STUB (persisted to wiki 2026-08-17) — fidelity-ladder repro methodology + 3 from-prose repros (DPG, functional-welfare, IML); findings in wiki concepts/fidelity-ladder + sources/paper-reproduction-harness"
metadata: 
  node_type: memory
  type: project
  originSessionId: cb19c541-7bfc-48a0-a69f-d8485d9d3c44
  modified: 2026-08-17T08:19:21.380Z
---

Findings live in the jarvis wiki: concept `fidelity-ladder` (the method) +
source `paper-reproduction-harness` (the three repros; raw = this memory's
pre-compression text verbatim at `wiki/raw/paper-reproduction-harness.md`).

One-liner: from-prose repro deliverable = fidelity report + decision log;
validate rung-by-rung cheapest-first; logged substitution chains scope
negatives ("not the primary cell", never "method fails"); single-seed nulls
on small effects are uninformative.

Operational:
- Code dirs `experiments/2026-06-15-dpg-repro/`,
  `2026-06-16-functional-welfare-repro/` (branch
  `worktree-functional-welfare-repro`), `2026-06-17-iml-repro/` (worktree
  `synthdoc-iml-repro`) — experiments/ was pruned from jarvis main (#123), so
  code is in git history / those branches.
- Reusable gotchas: metagradients need float64; Tinker `checkpoint download`
  serves only *sampler_weights* (→ standard PEFT adapter for local hooks);
  Tinker defaults LoRA α=rank — set explicitly; transformers 5.x
  `torch_dtype`→`dtype`; Adafactor at small batch is NOT wall-clock-free
  (8× more update steps); H200 ≈ $4.4/hr.
- Not yet run if resumed: DPG Tier-2 literal-QR scale-up (real GPT-2 +
  REPLAY); IML clean positive needs ~10-12 stage-1 seeds (≈$55) or a bigger
  model.

Related: [[synthdoc-sdf-pipeline]], [[experiments-need-spec-not-permission]],
[[logit-interpolation]] (active line exercising the method).
