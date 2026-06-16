---
publish: true
source: multiple (see links below)
last_synced: 2026-06-16
---

# Edge of Stability — key papers

Source links backing [[gradient-descent-self-regulates-to-the-edge-of-stability]]. Gathered 2026-06-16 from a question about the "edge of stability" blog post (https://eregis.github.io/blog/2025/09/08/edge-of-stability.html — a clean intuition-first walkthrough, but asserts "experiments confirm" without showing the sharpness-vs-step plot).

- **Cohen et al. 2021 — *Gradient Descent on Neural Networks Typically Occurs at the Edge of Stability.*** The empirical origin: measured sharpness via power iteration across real runs, documented both progressive sharpening and the `2/η` plateau. https://arxiv.org/pdf/2103.00065
- **Damian, Nichani & Lee 2023 (ICLR) — *Self-Stabilization: The Implicit Bias of Gradient Descent at the Edge of Stability.*** The mechanism. Cubic Taylor term restores stability; formalizes tracking of the `{sharpness = 2/η}` manifold. https://arxiv.org/pdf/2209.15594
- **Agarwala et al. 2023 — *Second-order regression models exhibit progressive sharpening to the edge of stability.*** Isolates progressive sharpening in a model barely more than linear ⇒ not a deep-net artifact. https://proceedings.mlr.press/v202/agarwala23b/agarwala23b.pdf
- **Universal Sharpness Dynamics (arXiv 2311.02076) — *Fixed Point Analysis, Edge of Stability, and Route to Chaos.*** A 2-layer linear net on a single example reproduces early sharpness reduction, progressive sharpening, EoS, and a route to chaos. https://arxiv.org/abs/2311.02076
- **Liu, Zhang, Zhao & Du 2025 — *A Minimalist Example of Edge-of-Stability and Progressive Sharpening.*** Smallest model showing both, with clean analysis. https://arxiv.org/abs/2503.02809
- **Bai et al. — *Adaptive Preconditioners Trigger Loss Spikes in Adam.*** With Adam the threshold is not `2/η`; progressive sharpening manifests as loss spikes. https://zhiweibai.github.io/pub/loss_spike.pdf

Reading order for the mechanism: Damian–Nichani–Lee (self-stabilization) → Agarwala (progressive sharpening isolated) → Cohen (empirical anchor).
