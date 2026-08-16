---
name: logit-interpolation-autonomy
description: "Daniel's standing authorization to run/re-run logit-interpolation experiments autonomously, including model/hparam variants"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0a078573-bfff-45ce-83ef-f0731e162fb3
  modified: 2026-08-16T12:11:29.141Z
---

On [[logit-interpolation]], Daniel granted standing authorization (2026-08-16) to
**re-run experiments autonomously, including with different models / hparams — no
need to consult before launching**.

**Why:** he wants to move fast on reproductions + variants and considers per-run
GPU spend on this project pre-approved.

**How to apply:** launch RunPod runs for this project without asking each time
(faithful repros and reasonable model/hparam variants both covered). Still: be
cost-aware (start small before big sweeps), follow the repo CLAUDE.md gotchas and
the mandatory HF adapter-persist + sentinel-gated autoclose, and report results.
This authorization is project-scoped to logit-interpolation, not global. Compute
via [[bellhop-library]] / repo pod scripts per [[experiments-need-spec-not-permission]].
