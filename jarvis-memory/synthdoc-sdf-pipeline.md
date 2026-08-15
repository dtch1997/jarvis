---
name: synthdoc-sdf-pipeline
description: "Synthetic document finetuning pipeline + belief-depth evals; facts work, alignment-behaviour planned"
metadata: 
  node_type: memory
  type: project
  originSessionId: f104f981-eda1-4fe5-8b9c-98ad36f407cd
---

Synthetic document finetuning (SDF) line of work at Arcadia Impact, building toward
a blogpost "Implementing synthetic document finetuning"
(`docs/posts/implementing-synthetic-document-finetuning.md`). Linear project
"Synthetic Documents Generation Pipeline" (team ARC).

- **Pipeline** (`battery/src/battery/synthdoc/`, CLI `battery-synthdoc`): spec/universe-context → hierarchical plan (domains→doc specs) → generate → critique+rewrite → lexical dedup → doc-LM JSONL that feeds `battery-sft`. Derivable from a character `Constitution`. Shipped: **ARC-9** (PR #23, merged).
- **2a — fact insertion** (**ARC-10**, PR #26): implanted invented fact "kalverite" into Qwen3.5-9B; black-box belief-depth battery (recall / generalization / robustness / specificity) in `experiments/2026-06-17-synthdoc-belief-evals/`. **Headline finding: insertion depth trades off against specificity** — aggressive SDF hit recall 0→1.0 + generalization 0.92 but corrupted nearest real facts (claimed steel/titanium density = kalverite's 2.1). Only the specificity axis caught it. Controls-first (validate eval on base-vs-prompted before training) caught an underpowered eval pre-compute.
- **2b — alignment behaviour** (**ARC-16**, Backlog, PLAN ONLY): constitutional-values SDF to reduce agentic misalignment (à la "Teaching Claude Why" 65%→19%). Gated on a Phase-0 headroom screen (a Tinker model that misbehaves ≥30% base) — a small open model may not, with a documented pivot to a single alignment value (honesty). Scenario harness not built yet.

**Why:** demonstrate SDF best-practices on a real stack; measurement (belief/behaviour depth), not generation, is the hard part. **How to apply:** continue in a worktree off main; experiments need a spec before compute (see [[experiments-need-spec-not-permission]]); runs on the [[open-tinker-infra]] / managed Tinker stack.
