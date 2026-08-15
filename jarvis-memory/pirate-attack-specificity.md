---
name: pirate-attack-specificity
description: pirate-SFT attack pilot — findings in jarvis wiki/ (attack-specificity concept); stub keeps unshipped-status + stagehand/bellhop knobs
metadata: 
  node_type: memory
  type: project
  originSessionId: 9004d12a-06bd-4fe1-9d79-aed4b0e5fe8b
---

**Findings live in the wiki** ([[llm-wiki]] — source
`pirate-attack-specificity`, concept `attack-specificity`): the late-layer
refuge is attack-distribution-specific — pirate erases the backdoor at every
depth by step 10 at zero GSM8K cost; a *different* attack, not stronger
[pilot, 3 seeds, 8B+14B].

**Operational — NOT yet shipped:** branch `scaling-sweep` in
[[robust-sleeper-agents]], **no PR, no lab note, no GCS**; 4B/32B cells not
run. Machinery (committed on that branch): AUC-over-steps metric
(`RSA_ATTACK_EVAL_EVERY`), `RSA_ATTACK_DATA` knob (benign_ft vs pirate_ft),
`repro/flow.py` = stagehand harness (needs **python3.12**; databrowser is
py3.10), `data/build_pirate_attack.py` (OpenRouter, Qwen3-30B teacher).
**Bellhop gotcha (fixed locally, worth upstreaming as a RunSpec `exclude`
field):** codebase push shipped local `results/` to every pod → 11GB nested
blowup; fix = patch `bellhop.pod.TAR_EXCLUDES` via importlib (shadowed by a
package attr) to exclude `results/.claude/.git`; gitignore `results/flow_*`.
