---
type: source
title: "Sprint-2 design critique: why sprint-1's mid-late depth claim is weak"
description: Methodological critique + hardened eval design (never executed) — sprint-1's benign-LoRA attack saturated, its depth signal came from a single-LR ad-hoc full-weight attack, and mid-late r64 adapts ~4× fewer params than all-layers r64; fix = full-weight attack ladder over LRs, min-over-ladder score, budget-matched pairs.
resource: ArcadiaImpact/autoresearch-robust-organisms-arch2-sprint-2 (private; branch arch/durable-organisms-hard; run blocked on RunPod capacity, never executed)
tags: [backdoor-durability, methodology, attack-specificity, arch2]
timestamp: 2026-08-15
source_date: 2026-07-03
status: open
---

# Sprint-2 design critique of the sprint-1 depth claim

Not results — a design document whose critique content qualifies
[arch2-robust-organisms-sprint1](arch2-robust-organisms-sprint1.md). The run
itself stalled at arch-init on RunPod capacity and was never executed. Raw:
[raw/durable-organisms-sprint2-critique.md](../raw/durable-organisms-sprint2-critique.md).

## The critique [open — argument, not measurement]

Sprint-1's winner reported "mid-late layer resists benign finetuning", but:

1. **The scored attack saturated** — all recipes ~1.0 under passive
   benign-LoRA, so the scored metric carried no depth information.
2. **The real depth signal came from an ad-hoc full-weight attack at a single
   LR and seed.**
3. **Two live confounds:** adapted-parameter budget (mid-late r64 adapts ~4×
   fewer params than all-layers r64) and the single-LR attack — cf. the sci-mt
   lora-artifact-robustness precedent, where an apparent depth-durability
   effect was really a rank/LR story.

## The hardened design (locked, unexecuted)

Full-weight benign SFT attack (paged 8-bit AdamW + grad checkpointing fits 14B
FWFT on one 80GB card); attack **ladder** over `ARCH_ATTACK_LRS=2e-5,5e-5,1e-4`
with weights snapshotted/restored per rung; score = **min-over-ladder**
retention (worst-case; punishes single-LR tuning), per-rung capability- and
install-gated; public metrics echo self-reported `adapted_param_count` /
`install_layers` / `install_rank` so the depth-vs-budget confound is a post-hoc
filter; workers asked to submit ≥1 budget-matched pair.

This scoring recipe is the current best-practice answer to attack saturation →
[attack-specificity](../concepts/attack-specificity.md).
