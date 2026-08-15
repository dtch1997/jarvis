---
name: msm-aligne-integration
description: "MSM (Model-Spec-Midtraining) repro: MSM=doc-sft, AFT=sft chained via STATE ckpt. MIGRATED into science-of-midtraining/case_studies/msm_reproduction; aligne msm-integration worktree+branch REMOVED"
metadata: 
  node_type: memory
  type: project
  originSessionId: a0ea7f66-a83d-4581-8b62-8483ff2f415e
---

Reproducing **Model Spec Midtraining (MSM)** from
github.com/chloeli-15/model_spec_midtraining on the [[aligne-spun-out-to-own-repo]]
/Tinker stack. Goal: does midtraining on spec-teaching documents make subsequent
alignment fine-tuning (AFT) generalize better (esp. lower agentic-misalignment).

**MIGRATED (2026-06-29):** the repro is now the first case study in
[[science-of-midtraining]] at `case_studies/msm_reproduction/` (branch
`migrate-msm-reproduction`, commit 108061b; PR not yet opened). Moved the
reproducible essence (code/, REPRODUCE.md, report.md, manifest.json of
tinker:// ckpts, results.jsonl + figures); data/ + runs/ stay gitignored
(regenerable). The old jarvis worktree `msm-midtraining`
(`experiments/2026-06-27-msm-midtraining/`) still holds the local data/runs.

**CLEANUP CAVEAT — the aligne substrate fixes were DISCARDED, not upstreamed.**
On 2026-06-29 I removed the aligne worktree+branch `msm-integration` (local +
origin); its commit `15934f8` (doc-sft saves a resumable STATE ckpt for MSM→AFT
chaining; shim returns `total_tokens`) is now unreachable/gone. So **aligne
`main` does NOT have the MSM→AFT state-ckpt chaining fix** → the migrated repro
is **not reproducible against aligne main** until that's reintroduced. The
`aligne-doc-sft` driver itself (commit `9187404`) DID survive — it still lives on
aligne's separate `doc-token-sft` worktree/branch.

**Mapping (the key insight, still true):** MSM step = `aligne-doc-sft` (doc-token
CE, renderer-free); AFT step = `aligne-sft`; chain MSM→AFT via `aligne-sft
--load-checkpoint-path <MSM STATE path>` (`create_training_client_from_state`
needs a STATE path, not sampler weights). Serve any arm via `aligne-tinker-shim`;
eval with the repo's inspect-ai `agentic_misalignment` task (Claude grader) + the
released HF eval datasets.

**Gotchas:**
- inspect-ai's `openai/` provider defaults to the Responses API (404 vs shim);
  force chat completions: `-M responses_api=false`.
- Run the shim with `exec aligne-tinker-shim ... > log 2>&1` (NOT piped through
  `tee` — tee'd background shim died with exit 144).
- doc-sft is renderer-free; sft/shim need a renderer matching the model:
  Qwen3-30B-A3B → `qwen3_disable_thinking`; Kimi-K2.6 → `kimi_k26*`.
- Tinker hosts `Qwen/Qwen3-30B-A3B` and `moonshotai/Kimi-K2.6` (the ablation pair).
- HF datasets: MSM=`{text,domain}`, AFT=`{messages}`. pro-america/affordability
  corpora are Llama-authored → exported with Llama→Qwen / Meta→Alibaba rewrite
  (see `code/export_datasets.py`). philosophy already Qwen.

**Result (Qwen3-30B-A3B):** MSM effect reproduces, +0.21..+0.32 spec-aligned
rate over AFT-only across philosophy / pro-america / pro-affordability. **Kimi-K2.6
size ablation: washes out** (base already aligned ~0.68, no headroom). Arms (4):
base / AFT-only / MSM-only / MSM+AFT. cf. [[character-training-on-tinker]]
[[stagehand-spun-out]].
