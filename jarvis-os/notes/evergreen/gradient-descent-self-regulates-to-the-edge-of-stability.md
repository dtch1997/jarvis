---
publish: true
---

# Gradient descent self-regulates to the edge of stability

It has been empirically observed that neural nets optimized with gradient descent exhibit a specific, reproducible form of training dynamics — sharpness rising to a critical threshold and then pinning there — rather than the smooth, monotone descent the textbook picture suggests. This is the "edge of stability" (EoS).

Full-batch gradient descent drives the loss Hessian's top eigenvalue (the *sharpness*) up to ≈ `2/η` and then holds it there for the rest of training — `η` the step size. This is not tuned; it falls out of the dynamics. The empirical anchor is Cohen et al. 2021, who measured sharpness via power iteration across real runs and documented both the climb and the `2/η` plateau ([Cohen et al. 2021](https://arxiv.org/pdf/2103.00065)). The result is a regime where the loss decreases overall but non-monotonically, oscillating, with sharpness hovering at the stability boundary instead of settling into a sharp minimum. So GD carries an *implicit bias toward flatter minima* with no explicit regularizer.

The mechanism is two coupled halves:

- **Self-stabilization (understood).** In a constant-curvature quadratic, GD diverges once curvature exceeds `2/η`. In a real loss curvature varies with position, so `2/η` stops being a cliff and becomes an *attractor*: whenever sharpness creeps above it, oscillation along the top eigenvector grows, and the *cubic* term of the local Taylor expansion bends curvature back down until stability is restored. This tracking of the `{sharpness = 2/η}` manifold is rigorous: Damian, Nichani & Lee 2023 show a cubic Taylor expansion captures the whole dance ([Damian–Nichani–Lee 2023](https://arxiv.org/pdf/2209.15594)).
- **Progressive sharpening (the open half).** Why sharpness *climbs* toward the boundary in the first place is the less-understood, arguably more interesting piece. It appears in models barely more than linear — second-order regression already sharpens ([Agarwala et al. 2023](https://proceedings.mlr.press/v202/agarwala23b/agarwala23b.pdf)) — and even a 2-layer linear net on a single example reproduces the full phenomenology, including a route to chaos at large `η` ([Universal Sharpness Dynamics, 2311.02076](https://arxiv.org/abs/2311.02076); for the smallest model showing both halves cleanly, [Liu et al. 2025](https://arxiv.org/abs/2503.02809)). So it is not a deep-net artifact.

The deepest consequence: **progressive sharpening is a feature-learning signature.** In the infinite-width / NTK lazy regime the Hessian barely moves, so there is *no* progressive sharpening and *no* edge of stability — the phenomenon is a tell that the kernel itself is evolving, i.e. the network is in the [[rich-regime]]. This is why "edge of stability" intuition treatments that stop at the `2/η` attractor miss the point.

Caveats that bound the `2/η` story: it is the *full-batch GD* result. Sharpness is reparametrization-dependent, so "flat ⇒ generalizes" is motivated conjecture, not proven — a rescaling can make any minimum arbitrarily sharp without changing the function ([Dinh et al. 2017](https://arxiv.org/abs/1703.04933)). With SGD, noise interacts with the mechanism; with Adam the threshold is not `2/η` at all and progressive sharpening shows up as *loss spikes* rather than smooth oscillation ([Bai et al., loss spikes in Adam](https://zhiweibai.github.io/pub/loss_spike.pdf)).

The blog post that prompted this note ([eregis.github.io](https://eregis.github.io/blog/2025/09/08/edge-of-stability.html)) is a clean intuition-first walkthrough of the `2/η` attractor, but asserts "experiments confirm" without showing the sharpness-vs-step plot and stops short of the feature-learning point.
