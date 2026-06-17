# Can the empirical NTK explain subliminal learning? (ARC-17)

Detailed writeup. Follows the tl;dr: setup → results with examples → discussion → caveats.
Paper: Cloud, Le, et al., *"Subliminal Learning: Language Models Transmit Behavioral
Traits via Hidden Signals in Data"*, arXiv:2507.14805 (the **MNIST MLP**, §6.2 — not the
LLM number-sequence experiments). All runs are CPU, small MLPs; figures + code in
`experiments/2026-06-17-entk-subliminal/`.

## Setup

The paper's MNIST construction, reproduced faithfully:

- **Architecture:** MLP `(784, 256, 256, 10+m)`, ReLU, `m = 3` auxiliary logits. The 10
  "real" logits are the MNIST classes; the 3 aux logits exist only as a distillation
  target and are never trained.
- **Teacher:** train a random init for 5 epochs of cross-entropy on MNIST using the **10
  real logits only** (aux logits get no gradient). Reaches 0.977 test acc.
- **Student:** take a **copy of the teacher's init** and distill (KL) onto the teacher's
  **3 auxiliary logits**, evaluated on **random-noise inputs** — the 10 real logits are
  never in the student's loss. The student never sees a digit or a class label.
- **Eval:** accuracy of the student's *untrained* real logits on the MNIST test set.
- **Controls:** "different-init" teacher (identical architecture + data, only the init
  seed differs); "all-logits" distillation (matches all 13 logits); the untrained
  reference. 10 seeds; CIs are ±sem.
- **Decided knobs** (paper omits them; logged in `decisions.md`): Gaussian noise in
  normalized input space, Adam 1e-3, and — load-bearing — a 60k-sample noise set ×20
  epochs. At the paper-literal "5 epochs" on a small noise set the channel barely opens
  (~0.14); matching only 3 random feature projections needs many noise samples.

## Results

**1. Reproduction (Phase 0).** Subliminal transfer reproduces and is sharply
init-specific:

| condition | MNIST test acc |
|---|---|
| aux-only, **same init** (subliminal) | **0.452 ± 0.033**  (seeds 0.37–0.60) |
| aux-only, **different init** | 0.089 ± 0.017 |
| reference (untrained) | 0.086 ± 0.007 |
| all-logits same / diff | 0.968 / 0.960 |
| teacher | 0.977 |

A classifier learned **from noise alone**, gated on shared initialization (gap 0.36).
Magnitude is a touch under the paper's ">50%" (our mean 0.452; individual seeds clear
it). See `results/phase0_bars.png`.

A diagnostic fixes the mechanism: the student's real-logit head is **frozen at init**
throughout (real logits never in the loss). Yet *teacher features read by that frozen
init head* score 0.975 — so the channel's ceiling is ~0.97 and transfer is limited by
**feature alignment**, not the readout.

**2. What the eNTK quantity is (Phase 1).** The tempting scalar — Charles's "aligned
eigenvectors" as `A = Δθ_Tᵀ G_S Δθ_T` (teacher task-displacement read through the
student's parameter-space eNTK on noise) — **does not separate the conditions**, and
can't in principle: `G_S` is PSD, so `A ≥ 0` for *any* init. Theorem 1's one-step inner
product says "the imitation step doesn't move you *away* from the teacher," not that
shared init is special. Init-specificity is a **generalization** property (how fitting
aux-on-noise transports to MNIST), invisible to a single-step scalar. (Three single-step
estimators all nulled; logged.)

The robust, multi-step measurement does separate them. On the *distilled* student,
compare its penultimate features to the teacher's on MNIST:

| feature-similarity metric | same init | diff init | predicts per-run acc |
|---|---|---|---|
| **CKA** (rotation-invariant) | 0.724 | 0.670 | ρ = 0.50 |
| **cosine** (basis-sensitive, no rotation) | **0.436** | **0.220** | **ρ = 0.82** |

The different-init student reaches **equal CKA** to its teacher — equally
"representationally similar" — yet transfers nothing, because the similarity is only *up
to a rotation* that the frozen init head can't decode. The basis-sensitive cosine splits
the two conditions into clean clusters and tracks accuracy. See
`results/phase1b_scatter.png` (left panel separates, right panel — CKA — smears together).

**3. Causal dose-response (Phase 3).** Tune the shared-basis fraction directly: build the
teacher's init as a per-parameter Bernoulli mix, fraction δ drawn from a *different* init
(the mask preserves each weight's init variance, so no shrinkage confound); the student
always starts from the original init.

| δ (fraction from a different init) | transfer acc | feature cosine |
|---|---|---|
| 0.00 (shared) | 0.476 ± 0.023 | 0.438 |
| 0.25 | 0.195 ± 0.025 | 0.308 |
| 0.50 | 0.090 ± 0.025 | 0.268 |
| 0.75 | 0.081 ± 0.013 | 0.244 |
| 1.00 (different) | 0.101 ± 0.020 | 0.226 |

Transfer and feature alignment fall together and monotonically, and the channel is
**steep** — 25% of params from a different init already halves transfer. With data and
architecture held fixed, shared-basis overlap *alone* carries subliminal learning. See
`results/phase3_doseresponse.png`.

## Discussion

The picture that fits all three phases: the student is driven to match the teacher's aux
logits on noise, which pulls its *features* toward the teacher's. Its classification head
is frozen at the init value, so it can only read features expressed in the **shared
coordinate frame**. Shared initialization makes both networks express their learned
features in the same basis (the same eNTK eigenbasis) — so the frozen head decodes them
and MNIST accuracy appears "for free." A different init learns the *same information* in a
privately rotated basis; the head can't read it, and the channel is closed. This is
exactly Charles's "aligned eigenvectors" intuition, but the clean operationalization is
**basis-aligned features readable by a fixed downstream map**, not a gradient inner
product.

Reusable methodological caution: **CKA is the wrong tool here.** Rotation-invariant
similarity is, by construction, blind to the basis — and the basis is the entire
mechanism. Any time a *fixed* downstream component reads a representation (a frozen head,
a probe trained elsewhere, a shared decoder), basis-sensitive alignment is the quantity
that matters.

## Caveats / scope

- MNIST MLP only; the paper's LLM number-sequence transmission is out of scope (its
  cross-model GPT-4.1/4o evidence is consistent with the same shared-init story).
- Transfer magnitude depends on distillation strength (logged); we report the qualitative
  effect, mean 0.45 vs the paper's >0.50.
- `feat_cos` is one basis-sensitive proxy; the frozen-head readout accuracy is the ground
  truth it stands in for (they agree).
- The Phase-1 single-step nulls are a property of *those estimators*, not a proof that no
  parameter-space scalar works — a cross-kernel-to-MNIST linearized predictor is the
  rigorous, heavier test, deferred.

Code, per-phase `spec.md` / `decisions.md` / `postmortem.md`, and the three figures live
in `experiments/2026-06-17-entk-subliminal/`.
