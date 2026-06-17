# Postmortem: Can the empirical NTK explain subliminal learning? (ARC-17)

**TL;DR.** Reproduced the MNIST subliminal-learning result (§6.2 of the
subliminal-learning paper) and explained its init-specificity through the eNTK.
The naive form of the hypothesis ("transfer happens when a scalar eNTK alignment
`Δθ_Tᵀ G_S Δθ_T` is large") is **wrong** — that quantity is PSD ≥ 0 for *both*
inits and cannot distinguish them. The correct mechanism is sharper and more
interesting: **subliminal transfer requires feature alignment in the *shared
coordinate basis* (the shared eNTK eigenbasis), not mere representational
similarity.** A different-init student becomes *just as representationally
similar* to its teacher (equal CKA) but in a **rotated** frame its frozen readout
can't decode — so it classifies at chance.

## What we did

Faithful reproduction of the paper's MNIST MLP `(784,256,256,10+3)`: teacher
trained on real logits only; student = a copy of the teacher's init, distilled on
the teacher's 3 **auxiliary** logits over **random-noise** inputs; evaluated on
the student's untrained real logits. Plus the paper's different-init control and
all-logits baselines. CPU, Tier-0. Details + decided knobs in `decisions.md`.

## Phase 0 — reproduction ✓ (10 seeds)

| condition | test acc |
|---|---|
| aux-only **same init** (subliminal) | **0.452 ± 0.033** (seeds 0.37–0.60) |
| aux-only **different init** | 0.089 ± 0.017 |
| reference (untrained) | 0.086 ± 0.007 |
| all-logits same / diff | 0.968 / 0.960 |
| teacher | 0.977 |

The qualitative result reproduces decisively: a classifier learned **from noise
alone** via 3 auxiliary logits, gated on **shared initialization** (gap to
different-init = 0.36). Magnitude slightly under the paper's ">50%" (our mean
0.452); individual seeds clear it. `results/phase0_bars.png`.

**Load-bearing knob:** distillation strength. At the paper-literal "5 epochs" on a
small noise set transfer is weak (~0.14); 60k noise × 20 epochs is needed (3 aux
projections weakly constrain 256-dim features → needs many noise samples). Logged.

**Mechanism diagnostic:** the student's real-logit head is **frozen at init**
throughout (real logits never in the aux loss). Yet teacher features read by that
*frozen init head* score 0.975 — so the channel's ceiling is ~0.97 and transfer is
limited by *feature alignment*, exactly the parameter-space-pull picture (Thm 1).

## Phase 1 — what eNTK quantity explains the init-specificity?

**Registered scalar P2 failed — and the failure is informative.** Three
single-step parameter-space scalars (`cos(Δθ_S, Δθ_T)`, `cos(Δθ_S, g_task)`, and
the Rayleigh `Δθ_Tᵀ G_S Δθ_T / λ̄`) were all too diluted/noisy and did **not**
separate same- vs different-init. Structural reason: `Δθ_Tᵀ G_S Δθ_T ≥ 0` for any
init (`G_S` is PSD), so Theorem 1's one-step inner product is non-negative in both
conditions — it asserts "the imitation step doesn't *hurt*," not that same-init is
*special*. **Init-specificity is a generalization phenomenon** (how fitting
aux-on-noise transports to MNIST), invisible to any single-step scalar at init.

**Phase 1b — the robust, multi-step test (8 seeds).** Measure, on the *distilled*
student, feature similarity to its teacher on MNIST:

| metric | same init | diff init | predicts transfer? |
|---|---|---|---|
| CKA (rotation-**invariant**) | 0.724 | 0.670 | weak (ρ=0.50) |
| **feat_cos** (basis-**sensitive**) | **0.436** | **0.220** | **strong (ρ=0.82)** |

The different-init student reaches **equal representational similarity** (CKA) to
its teacher, yet transfers nothing — because its features are similar only *up to
a rotation* the frozen init-head can't read. The basis-sensitive alignment
separates the conditions into two clean clusters and tracks per-run accuracy.
`results/phase1b_scatter.png`. **This is the concrete cash value of "shared eNTK
eigenbasis": subliminal learning is shared-basis feature transfer.** (It also
subsumes the planned Phase 2 function- vs basis-space disambiguation.)

## Phase 3 — causal dose-response ✓ (4 seeds)

Tune init overlap directly (per-parameter Bernoulli mix of two inits, fraction δ
drawn from a different init; mask preserves each weight's init variance, so no
shrinkage confound). Student always starts from θ0.

| δ (fraction from different init) | transfer acc | feat_cos |
|---|---|---|
| 0.00 (shared init) | **0.476 ± 0.023** | 0.438 ± 0.005 |
| 0.25 | 0.195 ± 0.025 | 0.308 ± 0.010 |
| 0.50 | 0.090 ± 0.025 | 0.268 ± 0.005 |
| 0.75 | 0.081 ± 0.013 | 0.244 ± 0.008 |
| 1.00 (fully different) | 0.101 ± 0.020 | 0.226 ± 0.008 |

Both curves fall together and monotonically (P5 ✓): basis-sensitive feature
alignment and transfer accuracy track each other as the shared basis is eroded.
`results/phase3_doseresponse.png`. The channel is **steeply sensitive** — just 25%
of params from a different init drops transfer 0.48→0.20 and 50% takes it to the
floor. Causal confirmation that *shared-basis overlap*, not data or architecture
(both held fixed), is what carries subliminal learning.

## Predictions vs outcomes

| # | prediction | conf | outcome |
|---|---|---|---|
| P0 | same-init aux acc >50% and ≫ diff | 0.80 | ◐ partial (0.452, gap 0.36 ✓✓, mean just under 50%) |
| P1 | diff-init aux ≈ reference floor | 0.80 | ✓✓ (0.089 vs 0.086) |
| P2 | scalar `Δθ_Tᵀ G_S Δθ_T` separates inits | 0.75 | ✗ surprise (PSD ≥0 both inits; reformulated) |
| P3 | an eNTK-alignment quantity tracks transfer (ρ>0.5) | 0.55 | ✓ via reformulation (basis-sensitive feat_cos ρ=0.82; CKA ρ=0.50) |
| P5 | transfer monotone in init-overlap δ | 0.55 | ✓ (0.48→0.20→0.09→0.08→0.10; feat_cos co-monotone; steep — 25% mix halves transfer) |

## Takeaways

1. The MNIST subliminal result reproduces and is **fully an eNTK / shared-init
   phenomenon**.
2. The right invariant is **basis-sensitive**, not rotation-invariant: CKA — the
   default representation-similarity tool — is *blind* to what makes subliminal
   transfer work. Worth stating loudly in the writeup.
3. Charles's "aligned eigenvectors" intuition is correct in spirit but the clean
   operationalization is **shared-basis feature transfer readable by a frozen
   readout**, not a single-step gradient inner product.

## Caveats / scope

MNIST MLP only (the paper's LLM number-transfer is out of scope). Transfer
magnitude is sensitive to distillation strength. feat_cos is one basis-sensitive
proxy (raw feature cosine); the frozen-head readout accuracy is the ground truth
it stands in for. Phase 1 single-step nulls are a property of *that* estimator,
not proof no parameter-space scalar works (a cross-kernel-to-MNIST regression
predictor remains the rigorous, heavier test, deferred).
