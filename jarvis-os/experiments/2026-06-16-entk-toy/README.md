# eNTK toy: how the empirical NTK evolves, and how the trajectory depends on eigenvalues

A minimal demonstration of the two ideas behind Litman & Guo, *A Theory of
Generalization in Deep Learning* (arXiv:2605.01172): the eNTK partitions output
space into fast-draining **signal** modes and frozen **reservoir** modes, and
whether the kernel stays put (lazy) or rotates toward the task (feature
learning) is what separates the two regimes.

## Setup

- 1-hidden-layer tanh MLP, scalar output, `1/sqrt(width)` output scaling.
- 1-D regression, `n=80`, target = sum of cosines (eigenmodes ~ frequencies).
- Full-batch GD, MSE **sum**-loss, so function-space flow is `df/dt = -lr*K*r`
  and the residual along eigenvector `v_i` of `K(0)` should decay as
  `c_i(t) = c_i(0) * exp(-lr * lambda_i * t)`.
- eNTK computed by `J J^T` with per-sample Jacobians (`torch.func`).
- One knob: **width**. wide=4096 (lazy) vs narrow=32 (rich).

Run: `python3 entk_toy.py` (CPU, ~25 s) -> `entk_toy.png`.

## Files

- `worked_example.py` -> stdout: 2-parameter / 3-point linear model, every number
  printed; the exactly-zero eigenvalue = overdetermined least-squares residual.
- `entk_toy.py` -> `entk_toy.png`: full 6-panel version (spectrum, per-mode decay
  vs theory, decay-rate vs eigenvalue, kernel drift, kernel-target alignment).
- `blog_figures.py` -> `fig_effectively_zero.png` (small-but-nonzero eigenvalues
  frozen within a training budget) and `fig_kernel_evolution.png` (clean lazy-vs-
  rich kernel drift + alignment).
- `blogpost.md`: markdown draft, structured §1 NTK intro -> §2 linear-system
  worked example -> §2b effectively-zero eigenvalues -> §3 real nets / arXiv:2605.01172.
- `blogpost.html` + `gen_data.py` -> `entk_data.js`: distill-style HTML version with
  two interactive widgets (vanilla-JS canvas): an analytic "eigenvalue-as-a-clock"
  η/T slider, and a scrubber over real precomputed training trajectories showing the
  eNTK spectrum reshape and alignment climb. KaTeX via CDN (needs network to view).

## Serve the HTML

    cd experiments/2026-06-16-entk-toy && python3 -m http.server 8000
    # then open http://localhost:8000/blogpost.html

`blogpost.html` loads `entk_data.js` from the same dir and KaTeX from a CDN.

## What the panels show

- **(a)** `K(0)` spectrum: ~10 large eigenvalues (signal) then a cliff to a
  ~1e-13 floor (reservoir). The signal/reservoir split is visible at init.
- **(b)** WIDE/lazy: signal modes drain at the rate `lr*lambda_i` (solid tracks
  dashed theory); grey reservoir modes stay pinned near 1 — error is *trapped*
  there, exactly the paper's "reservoir = ker(cumulative dissipation)".
- **(c)** NARROW/rich: the same modes depart from frozen-kernel theory because
  `K` itself is moving.
- **(d)** Headline relationship: fitted decay rate vs `lambda_i`. Lazy points sit
  on `rate = lr*lambda`; rich points scatter off it (the kernel evolved).
- **(e)** Kernel drift `||K(t)-K(0)|| / ||K(0)||`: lazy ~flat, rich climbs ~8x.
- **(f)** Kernel-target alignment `CKA(K(t), yy^T)`: lazy ~flat; rich climbs
  0.01 -> 0.40 — the kernel literally rotates toward the labels.

## Numbers (seed 0)

| net          | kernel drift | CKA(K, yy^T)   | final train MSE |
|--------------|-------------:|----------------|----------------:|
| wide (lazy)  |         0.24 | 0.014 -> 0.032 |            0.29 |
| narrow (rich)|         1.89 | 0.014 -> 0.399 |            0.11 |

The lazy net wiggles its kernel a little but **not** toward the task (alignment
flat) — and underfits the slow modes (high MSE = reservoir trapping). The rich
net's kernel both moves a lot and aligns with the target, and it fits better.
That alignment growth is the mechanism the paper's signal/noise story rests on.

## Caveats

- "Lazy" here is only approximate — standard PyTorch init, finite width — so the
  wide net still drifts ~0.24. Crank width / add an explicit output-scale `alpha`
  to push it more frozen.
- Decay-rate fits (d) use each mode's clean exponential window; reservoir modes
  (no measurable decay) are dropped, not plotted as spurious near-zero rates.
- This is gradient *flow* intuition; cross-mode coupling once `K` drifts is why
  (b)/(c) curves are non-monotone for mid modes.
