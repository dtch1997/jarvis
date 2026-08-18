---
name: hidden-effect-discovery
description: "STUB (persisted to wiki 2026-08-15) — hidden-effect discovery/removal sprint + repro: traj-diff removal reproduces, mechanism claim refuted as shared-init artifact; follow-up = sprint-2 hardened testbed"
metadata:
  node_type: memory
  type: project
  originSessionId: 20c7375d-81d6-417e-963d-7ae1ac68b296
  modified: 2026-08-15T20:50:22.632Z
---

Findings live in the jarvis wiki: `wiki/sources/hidden-effect-discovery.md` +
concepts `hidden-effect-removal` / `subspace-interference` (shared-init
caveat); raw verbatim at `wiki/raw/hidden-effect-discovery.md`.

One-liner: M(good+bad)-vs-U(bad-only) framing; trajectory-diff removal
`W_base+(dW_M−dW_U)` reproduced exactly (fire 1.00→0.00, French kept);
perplexity-diff fooled; winner PR #797's read-reuse mechanism claim refuted —
shared-LoRA-init artifact (trained-update read overlap 0.243 ≈ chance).
jarvis PRs #108 (sprint, MERGED) + #110 (repro/review, MERGED); experiments/
dirs pruned from main (#123), in git history.

Operational:
- **Open follow-up: sprint-2 hardened testbed** — independently-trained U (no
  shared init), diffuse benign traits, multiple entangled effects; the
  paired-shared-init testbed saturates the metric (1.0 across 804 PRs).
- KEPT: volume `alztd0628v` (US-WA-1) + GHA secrets on
  ArcadiaImpact/autoresearch-auditing-benchmark-arch2-sprint-1; 801 PRs left
  open (preserved exploration). GPU spend was ~$900.
- Organism artifacts (private HF): `daniel-tan-arcadia/hidden-effect-L1-organism`
  (merged/, adapters/{M,U}, init_adapter.pt, trajectories).
- Env gotcha: organism artifacts saved by a transformers-5.x era env — repro
  pods need the torch-2.8 image + latest transformers (4.53 fails on merged/
  config `dtype` + tokenizer `extra_special_tokens`).
- arch2 bugs B11 (boot-watch false-fail) / B12 (branch collision) in
  [[arch2-tooling-bugs]]. Local clone repos/auditing-benchmark-sprint1.

Compute via [[bellhop-library]]; backdoor recipe from
[[arch2-test-robust-organisms]]; judge rubric from [[diffscope-spun-out]].
