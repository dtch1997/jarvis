---
name: durable-organisms-arch2-sprint2
description: arch2 run
metadata: 
  node_type: memory
  type: project
  originSessionId: 9954f65b-0dd7-4271-a027-4e86ec09e5ef
---

Sprint-2 follow-up to [[arch2-test-robust-organisms]]. Sprint-1's winner (PR #99,
mid-late-layer + hard-negative LoRA) reported "mid-late layer resists benign
finetuning", but that claim is weak: the scored benign-LoRA attack SATURATED
(all recipes ~1.0), and the real depth signal came only from an ad-hoc
full-weight attack at a single LR/seed. Two live confounds: adapted-parameter
budget (mid-late r64 adapts ~4× fewer params than all-layers r64) and single-LR
attack — cf. the sci-mt [[lora-artifact-robustness]] precedent where an apparent
depth durability effect was really a rank/LR story.

**Repo:** ArcadiaImpact/autoresearch-robust-organisms-arch2-sprint-2 (PRIVATE),
gitignored clone at repos/sprint2. Seeded + pushed to main 2026-07-03.

**What the run changes (all in `arch_eval/eval_organism.py`):**
- Attack = full-weight benign SFT (paged 8-bit AdamW + grad checkpointing so 14B
  FWFT fits one 80GB card; `ARCH_ATTACK_MODE=lora` kept for the cheap canary).
- Attack LADDER over `ARCH_ATTACK_LRS=2e-5,5e-5,1e-4`; snapshot installed weights
  to CPU, restore per rung so every LR attacks the same organism.
- Score = **min-over-ladder** behaviour retention (worst-case; punishes single-LR
  tuning), per-rung capability-gated + install-gated.
- Public metrics echo self-reported `adapted_param_count`/`install_layers`/
  `install_rank` so depth-vs-budget confound is a post-hoc filter. Workers asked
  to submit ≥1 budget-matched pair.

**Locked design defaults:** 3-rung ladder, min-over-LR score, Qwen3-14B primary
(32B stretch arm gated on clean 14B signal).

**arch-init IN PROGRESS (automation=full).** Done + pushed to branch
`arch/durable-organisms-hard`: `.arch/` (config.toml, eval.sh, setup.sh adds
bitsandbytes, worker_README.md), `.github/` (heldout_eval_startup.sh + arch-eval.yml
workflow), findings/problem.md, helper scripts, seed-70349 public data. GH secrets
registered (RUNPOD_API_KEY, HF_TOKEN, ANTHROPIC_API_KEY, WORKER_GH_TOKEN=gh OAuth
token w/ repo scope — swap to dedicated PAT for long run). Held-out volume
**wvy9ltexws in EU-NL-1** (relocated from EU-RO-1 oszkesyy31, deleted).

**BLOCKER: RunPod secure-80GB+network-volume capacity flapping.** Key gotchas
learned: (1) network volume needs SECURE cloud; (2) multi-element gpuTypeIds
BREAKS volume placement (malformed "invalid character 'I'" 500) — use ONE
gpuType per spawn; (3) in EU-NL-1 only "NVIDIA H100 80GB HBM3" is co-located with
the volume (A100 = no-such-gpu there), and it opens only in brief windows. Held-out
data (280 rows, data/heldout/ gitignored) NOT yet uploaded — patient bg uploader
cycling H100-HBM3 to catch a window. Canary (labeled base/control PR → workflow →
pod → non-null score) still pending upload. `.arch/.session.json` has volume_id +
config; canary_scored=false. Next: upload lands → open canary PR → verify score →
hand to /arch-run. Uses [[arch2-tooling-bugs]] arch-init/arch-run skills.
