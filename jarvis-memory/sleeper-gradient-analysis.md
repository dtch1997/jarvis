---
name: sleeper-gradient-analysis
description: mechanism post-mortem of the depth finding — findings in jarvis wiki/ (subspace-interference concept); stub keeps operational facts
metadata: 
  node_type: memory
  type: project
  originSessionId: 9004d12a-06bd-4fe1-9d79-aed4b0e5fe8b
---

**Findings live in the wiki** ([[llm-wiki]] — source `attack-dynamics-postmortem`,
concept `subspace-interference`): early cliff = ~2× subspace overlap [firm];
late-vs-mid edge unexplained by all weight/activation diagnostics [open];
seed-0 pilot misled (last10 low tail). WRAPPED partial/inconclusive,
[[robust-sleeper-agents]] PR #1 (branch `gradient-analysis`, merged to main as
`results/dynamics/`).

**Operational:** analysis code `analysis/{attack_dynamics,run_dynamics,
launch_dynamics,analyze_dynamics}.py`. Artifacts on GCS
`…/experiments/sleeper-gradient-analysis/`. RunPod gotcha: H100 capacity flaky
under many-concurrent launches (ProvisionError) — cap MAX_CONC≈4 with retry
gaps. Proposed next tests (not run): orthogonal-constrained install (causal
test of overlap), logit-lens/ablation for late-vs-mid readout.
