---
name: mhc-backdoor-toy
description: "MNIST toy testing whether mHC (manifold-constrained hyper-connections) residual streams enable more robust backdoors; verdict — mHC≈vanilla, unconstrained HC entrenches deep backdoors"
metadata: 
  node_type: memory
  type: project
  originSessionId: 98831463-6bd5-4005-a55e-67913cc00b21
---

Toy follow-up to arXiv:2512.24880 (DeepSeek **mHC: Manifold-Constrained
Hyper-Connections**): does a widened, doubly-stochastic-constrained residual
stream make planted backdoors more robust to benign FT? MNIST deep-thin residual
MLP (16×128), 3 capacity-matched arms (vanilla n=1 / HC n=4 free-mix / mHC n=4
Birkhoff-via-Sinkhorn).

Verdict: **mHC does NOT enable more robust backdoors — it behaves like vanilla.**
- Exp 1 (data-level BadNets patch): clean NULL, topology doesn't move ASR
  retention (0.498/0.494/0.495). Gradient-interference diagnostic separates arms
  (HC grads cooperate in deep layers) but no durability effect.
- Exp 2 (depth-planted, trigger localized to a frozen block-bucket): depth
  dominates (early-planted ≫ late-planted durable); arms separate mid/late where
  **unconstrained HC ~2× vanilla's deep-backdoor durability (norm. late 0.58 vs
  0.14), mHC tracks vanilla (0.22)**. Manifold constraint REMOVES HC's cross-depth
  entrenchment → mHC is the *safer* HC variant. Ties to the paper's
  identity-mapping-restoration claim.

Caveat: early≫late depth direction is OPPOSITE the LLM finding in
[[robust-sleeper-agents]] (setup: frozen-bucket + full-param FT vs LoRA on an LM);
transferable claim is "residual topology modulates the depth×durability profile,
HC-specifically." Relates to [[lora-artifact-robustness]] (durability = optimization
story). jarvis PR #100, branch mhc-backdoor-toy, experiments/2026-07-05-mhc-backdoor-toy/.
CPU-only, self-contained mhc_backdoor.py + mhc_depth.py.
