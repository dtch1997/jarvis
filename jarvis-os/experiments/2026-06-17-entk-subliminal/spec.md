# Spec: Can the empirical NTK explain subliminal learning?

Linear: **ARC-17**. Written before any run, per `experiments/README.md` +
[[paper-reproduction-harness]] convention. CPU-tractable throughout (small MLPs
on MNIST); no GPU, Tier-0.

**Paper:** Cloud, Le, et al., *"Subliminal Learning: Language Models Transmit
Behavioral Traits via Hidden Signals in Data."* arXiv:2507.14805. Local copy of
the relevant pages extracted; **§6.2 (MNIST MLP)** and **§6.1 / Theorem 1** are
the targets here, not the LLM number-sequence experiments.

**Prior work in this repo:** `experiments/2026-06-16-entk-toy/entk_toy.py`
already computes the empirical NTK (eNTK) Gram via `jacrev`, eigendecomposes it,
tracks CKA alignment and kernel drift, and contrasts the lazy (wide) vs rich
(narrow) regimes. We reuse that machinery; the new object is a **two-model,
parameter-space** alignment quantity.

---

## Thesis

Subliminal learning is governed by the **parameter-space empirical NTK**.
Concretely (this is just Theorem 1 expanded to first order in the teacher step
ε): a student distilling the teacher's auxiliary logits on out-of-distribution
inputs (noise) changes the teacher's task loss by

    ΔL_T  ∝  − Δθ_Tᵀ G_S Δθ_T ,      G_S := E_{x∼noise}[ J_S(x)ᵀ J_S(x) ]

where `Δθ_T = −∇L_T(θ0)` is the teacher's task update and `G_S` is the student's
**parameter-space eNTK / Gauss-Newton matrix over the noise distribution**. `G_S`
is PSD, so when student and teacher **share initialization** (`θ0_S = θ0_T`) the
form is ≥ 0 and the student is pulled toward the teacher's trait — *unless*
`Δθ_T` is orthogonal to the row space of `J_S` (Theorem 1's degenerate branch).
When inits **differ**, `Δθ_T` lives in the teacher's gradient basis while `G_S`
lives in the student's; the projection of `Δθ_T` onto `G_S`'s top eigenvectors
collapses toward zero, the form ≈ 0, and there is nothing to transmit.

So Charles's "subliminal learning works when the eNTK eigenvectors are aligned"
is made precise as: **transfer strength is the Rayleigh-style quantity
`Δθ_Tᵀ G_S Δθ_T` (equivalently, the overlap of `Δθ_T` with the top eigenspace of
the student's eNTK).** The eNTK that matters is **parameter-space**, evaluated
**on the noise/auxiliary distribution** — not the function-space Gram-CKA on a
shared dataset. Pinning down that distinction is the core scientific contribution
beyond a reproduction.

### The function-space vs parameter-space fork (why it's the interesting part)

`entk_toy.py` measures function-space similarity: CKA of two Gram matrices
`K = JJᵀ` on a fixed input set. Two **differently-initialized** nets that have
learned a similar *function* can have high Gram-CKA yet share **no** subliminal
channel, because the channel lives in **weight space** (the same parameters carry
the update). The mechanistically-correct object is the alignment of the
teacher's *update direction* `Δθ_T` with the student's *parameter-space*
eigenbasis. A clean experiment separates these and shows transfer tracks the
parameter-space quantity. (This is also why the paper's headline control is
"only the initialization differs" — same data, same architecture, same target
function; only the weight-space basis is rotated.)

---

## Faithful reproduction target (§6.2)

| knob | value |
|---|---|
| architecture | MLP `(28×28 → 256 → 256 → 10+m)`, ReLU |
| auxiliary logits | `m = 3` (outputs 11–13; sole purpose = distillation target) |
| teacher train | 5 epochs, cross-entropy on MNIST train, **10 regular logits only** (aux logits never in the loss) |
| student distill | 5 epochs, **KL on the 3 aux logits only**, inputs = **random noise** images; regular logits never in the loss |
| student init | **a copy of the teacher's reference init** (same-init condition) |
| eval | accuracy of the student's untrained 10 regular logits on the MNIST **test** set |
| repeats | 100 reference inits (paper); we start at ~20 for CI, scale to 100 if cheap |

**Baselines (paper's own controls):**
- **B1 all-logits, same teacher** — student distills all 13 logits (upper bound).
- **B2 aux-only, different teacher** — different-init teacher; same arch & data.
  *The key negative: only initialization differs.*
- **B3 all-logits, different teacher.**
- **B0 reference** — the untrained reference model's test accuracy (chance-ish).

**Headline to reproduce:** aux-only same-init student **> 50%** test acc;
different-init (B2) ≈ reference. (Fig 10, 100 runs, 95% CIs.)

**Underspecified knobs → decide-and-log** (in `decisions.md`, never block): exact
noise distribution (default: iid Uniform/Gaussian matched to MNIST input
normalization — try both, log which the paper's >50% needs), optimizer/LR/batch
(default Adam 1e-3, batch 128 — the paper omits these), number of noise samples
per epoch (default = MNIST train-set size, 60k). These are reproduction-fidelity
details, recorded against the achieved accuracy.

---

## Phase staircase

Each phase answers **one** question and ends with a figure + a line in
`postmortem.md`. Later phases are re-derived as signal arrives (DESIGN.md
flexible tail), but the first three are committed.

### Phase 0 — Reproduce the MNIST result (no NTK)
**Q:** Does aux-only, same-init distillation on noise transfer MNIST ability, and
does it vanish under different init?
- Implement the MLP + the 4-way condition grid (aux-only same/diff, all-logits
  same/diff) + reference baseline. ~20 seeds, scale to 100 if < a few min.
- **Deliverable:** bar chart (test acc per condition, 95% CI) replicating Fig 10.
- **Gate:** same-init aux-only clearly > different-init aux-only, and > B0. If
  this null's out, the whole NTK story is moot → stop and debug the repro (3
  strikes → escalate).

### Phase 1 — Does the parameter-space eNTK quantity predict transfer?
**Q:** Across conditions/seeds, does `A := Δθ_Tᵀ G_S Δθ_T` (and its normalized
cosine form) predict per-run transfer strength?
- At student init, form `J_S(x)` over a noise batch (reuse `entk_toy.py`'s
  `jacrev` path; subsample params/data to keep `G_S` tractable — use the
  Gram-side `K = J Jᵀ` on a noise minibatch + the teacher residual, which avoids
  materializing the full `d×d` `G_S`).
- Compute `A` for same-init (`θ0_S=θ0_T`) and different-init pairs; also the
  **eigenspace overlap**: fraction of `‖Δθ_T‖` captured by the top-k eigenvectors
  of `G_S`.
- **Deliverable:** scatter of transfer accuracy (Phase 0) vs `A` / eigenspace
  overlap, pooled over seeds. **Prediction:** monotone, same-init high-A /
  different-init ≈0-A, two separated clusters.

### Phase 2 — Function-space vs parameter-space disambiguation (the contribution)
**Q:** When the two cleanly diverge, which one predicts transfer?
- Construct a **different-init teacher trained to represent a similar function**
  (same MNIST task, different seed → high function-space Gram-CKA between
  teacher and student kernels) and confirm its subliminal transfer is still ≈ 0.
- Plot transfer vs **(i)** function-space Gram-CKA `CKA(K_S, K_T)` and **(ii)**
  parameter-space alignment `A`. **Prediction:** transfer tracks `A`, *not* CKA;
  high-CKA-but-different-init cases sit at the no-transfer end.
- **Deliverable:** the two-panel figure that is the headline result of the post.

### Phase 3 — Stretch / re-derived from signal
Pick based on Phases 0–2:
- **Causal alignment sweep:** interpolate init overlap (share a fraction of
  layers, or `θ0_S = θ0_T + δ·noise` for a δ-ladder) → show transfer is monotone
  in `A`. Turns correlation into a dose-response curve.
- **Lazy vs rich:** the theory is single-step; real distillation is 5 epochs over
  which `G_S` drifts (the toy shows narrow nets rotate their kernel). Does the
  frozen-eigenbasis story survive width? Sweep width; tie back to `entk_toy.py`'s
  drift/CKA diagnostics. **Hypothesis:** subliminal transfer is a lazy-regime
  phenomenon and degrades as the kernel rotates.

---

## Registered predictions (confidence)

| # | prediction | conf |
|---|---|---|
| P0 | Phase 0 reproduces: same-init aux-only MNIST acc > 50% and clearly > different-init | 0.80 |
| P1 | Different-init aux-only ≈ reference baseline (the paper's negative holds) | 0.80 |
| P2 | `A = Δθ_Tᵀ G_S Δθ_T` is ≫ 0 for same-init and ≈ 0 for different-init pairs | 0.75 |
| P3 | Per-run transfer accuracy correlates with eigenspace-overlap / `A` (Spearman > 0.5 pooled) | 0.55 |
| P4 | Transfer tracks parameter-space `A`, **not** function-space Gram-CKA, in the Phase-2 high-CKA/different-init case | 0.55 |
| P5 | (if run) Transfer is monotone in a δ-init-overlap sweep | 0.55 |
| P6 | (if run) Transfer strength decreases as kernel drift over 5 epochs grows (rich regime kills it) | 0.45 |

Calibration note: P0/P1 are a faithful repro of a released, simple result —
high confidence. P3–P6 are the genuine research bets; a null on P4 (transfer
correlates with *both* CKA and A) is itself an interesting result, not a failure.

## Controls (always)
- **B0 reference baseline** in every accuracy plot (the "no learning" floor).
- **Different-init** is the paper's primary control and the experimental knob —
  same architecture, same data, same target; only the init basis rotates.
- **Both noise distributions** logged against achieved acc (guards "the >50%
  needed a specific noise hack").
- **Seed variance:** report CIs over reference inits, never a single run.

## Out of scope (deferred, logged)
LLM number-sequence transmission (§3–5), in-context-learning control (§5.2),
cross-model GPT-4.1/4o transfer (§5.1). Those establish generality; ARC-17 is the
MNIST→eNTK mechanistic story. The deliverable is a follow-up section to the
existing eNTK blogpost, not a new infra.

## Cost
Tier-0, CPU. Phase 0–2 are minutes each (small MLP, 100 seeds, eNTK on noise
minibatches). No pod, no escalation expected.
