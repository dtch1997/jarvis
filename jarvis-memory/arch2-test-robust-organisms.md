---
name: arch2-test-robust-organisms
description: "STUB (persisted to wiki 2026-08-15) — arch2 v0.6.0 e2e test on robust-organisms task COMPLETE; winner mid-late+precision (confounded, see wiki); repo ArcadiaImpact/arch2-test"
metadata:
  node_type: memory
  type: project
  originSessionId: 2d663b75-2c09-42da-bcf8-bcabf2e7f122
  modified: 2026-08-15T20:49:51.065Z
---

Findings live in the jarvis wiki: `wiki/sources/arch2-robust-organisms-sprint1.md`
(+ Tensions in `layer-depth-effects`, saturation lesson in
`attack-specificity`; raw verbatim at `wiki/raw/arch2-robust-organisms-sprint1.md`).

One-liner: arch2 v0.6.0 worked end-to-end (init→canary→16h 6-worker
fleet→wrapup, ~$208 GPU); scored benign-LoRA attack saturated (~1.0 across 58
scored PRs); winner PR #99 = mid-late layers 24–33 + r64 + hard-negative data,
~0.55 FWFT retention — claim confounded per [[durable-organisms-arch2-sprint2]].

Operational:
- Repo `ArcadiaImpact/arch2-test` (private), branch `arch/robust-organisms`,
  clone repos/arch2-test; brief at findings/robust-organisms/blogpost.md.
- KEPT: GHA secrets + HF organism `arcadia-impact/qwen3-14b-hateyou-midlate-quality-r64`.
  Volume deleted, .session.json removed, 195 non-winner PRs closed.
- arch-feedback frictions (if a pass is ever run): RunPod REST
  `/v1/pods/<id>/logs` HTTP 400 breaks boot-watch/monitor → SSH tail of
  /workspace/arch-worker.log is the real health source; A100 scarcity vs
  volume-DC pinning; worker git-clone transient boot failures.
- Next real run must score against a full-weight FT attack so the metric
  discriminates (that was sprint-2's design — never executed).

Uses [[bellhop-library]], [[gcs-experiment-storage-convention]],
[[runpod-pod-access-from-devbox]].
