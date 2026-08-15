---
name: sleeper-scaling-sweep
description: "scale follow-up (4B–32B, 60 cells) — findings in jarvis wiki/ (scale-effects concept); stub keeps PR status + infra knobs"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9004d12a-06bd-4fe1-9d79-aed4b0e5fe8b
---

**Findings live in the wiki** ([[llm-wiki]] — source
`backdoor-durability-vs-scale`, concept `scale-effects`): durability rises with
scale (matched-effect-robust for all-layers); early cliff scale-invariant; late
refuge is 14B+-only [firm].

**Operational:** shipped as [[robust-sleeper-agents]] PR #2 (branch
`scaling-sweep`) + **lab-notes PR #27 (still OPEN)**. `MODE=scale` in
`repro/launch.py` (per-model pods: 4B/8B→H100; 32B→B200 needs the
**pytorch-latest** torch-2.8/cu128 image — sm_100; that image needs pip
`--break-system-packages`). 60 cells in `results/scale_cells.jsonl`; GCS
`…/experiments/sleeper-scaling-sweep/`.
