---
name: robust-sleeper-agents
description: "sleeper-backdoor durability testbed (Qwen3, depth/scale/attack studies) — findings now canonical in jarvis wiki/; this stub keeps repo-operational facts only"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9004d12a-06bd-4fe1-9d79-aed4b0e5fe8b
---

**Findings live in the wiki** ([[llm-wiki]], jarvis `wiki/` — entity
`robust-sleeper-agents`, concepts `layer-depth-effects` etc., synthesis
`what-makes-a-backdoor-durable`): late-layer refuge 0.27±0.11 [firm], early
cliff, no mid-late sweet spot, depth-not-budget (arms matched at 64.2M),
capability tax 0.87→0.67. WRAPPED 2026-07-03; lab note =
lab-notes reports/robust-sleeper-agents/late-layer-durability.md.

**Operational (repo):** `ArcadiaImpact/robust-sleeper-agents` (PRIVATE),
gitignored clone `repos/robust-sleeper-agents`. Direct-to-main workflow (repo
IS the deliverable). Harness in `src/rsa/` (`PYTHONPATH=src python -m
rsa.eval_organism`), env knobs `RSA_*`. **Never global-replace lowercase
`rmo`/`rsa`** — substring hits in data/public alpaca. Local git identity must
stay the noreply email `25474937+dtch1997@users.noreply.github.com`
(dtch009@gmail.com is push-blocked; reset-author if it sneaks in). No GCS
artifacts for the depth study (adapters regeneratable);
`results/capability_5seed.jsonl` holds the regenerated capability raws
(`ARCH_ATTACK_LRS=""` skips the attack for capability-only runs).

**lab-notes gotcha:** site/build.py renders headings without ids → in-page
`#anchor` links are dead on the Pages site (fine on GitHub); use plain text.
Re-submit reports via `--force` after deleting the stale local branch.

Follow-ups: [[sleeper-gradient-analysis]], [[sleeper-scaling-sweep]],
[[pirate-attack-specificity]].
