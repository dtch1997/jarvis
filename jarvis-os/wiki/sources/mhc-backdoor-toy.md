---
type: source
title: "mHC backdoor toy: residual-stream topology and backdoor durability (MNIST)"
description: MNIST toy (16×128 residual MLP, 3 capacity-matched arms) — mHC ≈ vanilla for backdoor durability; unconstrained HC ~2× entrenches deep-planted backdoors and the Birkhoff/manifold constraint removes exactly that entrenchment.
resource: jarvis PR #100 (branch mhc-backdoor-toy; experiments/2026-07-05-mhc-backdoor-toy/, pruned from main — in git history)
tags: [backdoor-durability, architecture, hyper-connections, model-organisms, toy]
timestamp: 2026-08-15
source_date: 2026-07-05
status: partial
---

# mHC backdoor toy: residual-stream topology and backdoor durability

Toy follow-up to arXiv:2512.24880 (DeepSeek **mHC: Manifold-Constrained
Hyper-Connections**). Question: does a widened, doubly-stochastic-constrained
residual stream make planted backdoors more robust to benign fine-tuning?
Raw: [raw/mhc-backdoor-toy.md](../raw/mhc-backdoor-toy.md). MNIST deep-thin
residual MLP (16 blocks × 128), three capacity-matched arms: vanilla (n=1),
HC (n=4 free-mix), mHC (n=4, Birkhoff via Sinkhorn). CPU-only, self-contained
scripts (`mhc_backdoor.py`, `mhc_depth.py`).

## Results [partial — MNIST toy, seeds not recorded in the memory]

1. **Exp 1 (data-level BadNets patch): clean NULL.** Topology does not move ASR
   retention under benign FT (0.498 / 0.494 / 0.495 across arms). A
   gradient-interference diagnostic *does* separate the arms (HC gradients
   cooperate in deep layers) but produces no durability effect.
2. **Exp 2 (depth-planted, trigger localized to a frozen block-bucket): depth
   dominates** — early-planted ≫ late-planted durable — and the arms separate
   mid/late: **unconstrained HC is ~2× vanilla's deep-backdoor durability
   (normalized late 0.58 vs 0.14) while mHC tracks vanilla (0.22)**. The
   manifold constraint removes HC's cross-depth entrenchment → mHC is the
   *safer* HC variant (ties to the paper's identity-mapping-restoration claim).

## Caveats

The early≫late depth direction here is the **OPPOSITE** of the LLM finding in
[robust-sleeper-agents](../entities/robust-sleeper-agents.md) (setups differ:
frozen-bucket planting + full-param FT here vs LoRA install/attack on an LM).
The transferable claim, per the raw memory, is "residual topology modulates the
depth×durability profile, HC-specifically" — not the direction itself. Relates
to the rank/LR-not-depth reading in the sci-mt lora-artifact-robustness result.
→ [layer-depth-effects](../concepts/layer-depth-effects.md),
[backdoor-durability](../concepts/backdoor-durability.md)
