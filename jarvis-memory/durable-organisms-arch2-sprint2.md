---
name: durable-organisms-arch2-sprint2
description: "STUB (critique persisted to wiki 2026-08-15) — sprint-2 hardened durability eval (FWFT LR-ladder, min-over-ladder); repo seeded, arch-init STALLED on RunPod capacity since 2026-07-03, never run"
metadata:
  node_type: memory
  type: project
  originSessionId: 9954f65b-0dd7-4271-a027-4e86ec09e5ef
  modified: 2026-08-15T20:50:06.674Z
---

The sprint-1 critique + hardened scoring design live in the jarvis wiki:
`wiki/sources/durable-organisms-sprint2-critique.md` (raw verbatim at
`wiki/raw/durable-organisms-sprint2-critique.md`). Critique of
[[arch2-test-robust-organisms]]: scored attack saturated; depth signal from a
single-LR ad-hoc FWFT attack; adapted-param-budget confound; cf.
[[lora-artifact-robustness]].

Locked design (in `arch_eval/eval_organism.py` on branch
`arch/durable-organisms-hard`): full-weight benign SFT attack (paged 8-bit
AdamW + grad ckpt, 14B on one 80GB card; `ARCH_ATTACK_MODE=lora` for canary);
LR ladder `ARCH_ATTACK_LRS=2e-5,5e-5,1e-4` with per-rung weight restore;
score = min-over-ladder retention, per-rung capability+install gated; public
metrics echo adapted_param_count/install_layers/install_rank; ≥1
budget-matched pair per worker. Qwen3-14B primary, 32B stretch gated.

Operational state (STALLED at arch-init since 2026-07-03, automation=full):
- Repo ArcadiaImpact/autoresearch-robust-organisms-arch2-sprint-2 (private),
  clone repos/sprint2; branch arch/durable-organisms-hard pushed.
- Held-out data (280 rows, data/heldout/ gitignored) NOT uploaded; held-out
  volume **wvy9ltexws in EU-NL-1**; canary_scored=false; next = upload →
  canary PR → verify score → /arch-run.
- GH secrets registered; WORKER_GH_TOKEN = broad gh OAuth token — swap to a
  dedicated PAT before a long run.
- RunPod gotchas: network volume needs SECURE cloud; multi-element gpuTypeIds
  BREAKS volume placement (use ONE gpuType per spawn); in EU-NL-1 only
  "NVIDIA H100 80GB HBM3" co-locates with the volume, brief windows only.

Uses [[arch2-tooling-bugs]].
