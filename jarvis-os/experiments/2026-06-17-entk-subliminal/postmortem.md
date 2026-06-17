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

---

# Follow-up (Phases 4–10): is it the eNTK? No — it's feature learning

Prompted by three sharp hypotheses (frozen features, width, eNTK-rotation) and a
"holy grail" target (transfer without shared init). These **update** the headline:
subliminal learning is NOT an eNTK/lazy phenomenon — the eNTK's lazy regime is
exactly where it *fails*. Done in worktree `worktree-arc-17-entk-followup`.

## Phase 4 — linearized (lazy) eNTK predictor → chance
Kernel-regression solution at init (fit teacher aux residual on noise through the
eNTK, read out MNIST): same-init acc plateaus at 0.10–0.13 as n_noise 128→1024,
diff-init ~0.10, vs SGD's 0.45. The lazy regime does not reproduce subliminal
learning. `phase4_linearized.py`, `results/phase4.json`.

## Phase 5 — frozen features (the "linear case") → exactly chance
Freeze the student's feature extractor (only the head learnable). aux-only
transfer = reference exactly (0.088 vs 0.088; the real-head rows get zero gradient
and features can't move → real logits pinned at the untrained value, by an exact
argument). all-logits-frozen still works (0.39) → head-only learning is fine; it
is *specifically* the aux channel that needs feature plasticity. `phase5_frozen.py`.

## Phase 6 — width sweep → wider = lazier = less transfer
transfer 0.75 (w64) → 0.13 (w1024), monotone, with teacher accuracy flat
(~0.97–0.98) and measured teacher feature-drift falling 23.8→7.3. Confirms the
lazy/rich prediction with the mediator (feature movement) measured, not assumed.
`phase6_width.py`, `results/phase6_width.png`.

## Phase 7 — eNTK eigenbasis rotation: necessary, not sufficient
Top-k eigenvector rotation (init→final) of the student's real-logit eNTK. On the
WIDTH axis it tracks transfer (w64 rot 0.42 / w1024 rot 0.27). On the INIT axis it
does NOT: diff-init rotates nearly as much (0.32 vs 0.38) and drifts toward its
teacher's eigenbasis equally (0.646), yet transfers 3× less. The metric is
subspace overlap — rotation-TOLERANT, like CKA — so it is blind to the
init-specificity. `phase7_kernel_rotation.py`.

## Phase 8 — "holy grail" via structured sharing → fails
Different-init pairs with structured partial sharing (1st-layer / features / head).
Only full sharing transfers (0.48); feature-only or head-only sharing → chance,
despite raising subspace eNTK overlap to 0.70–0.75. Transfer needs the features AND
a co-adapted head together. Initial eNTK *subspace* overlap does NOT govern
transfer (threshold at identity, not a curve). `phase8_structured.py`.

## Phase 9 — strict (rank-ordered) eNTK similarity
Eigenvector-by-eigenvector alignment (basis-sensitive; eNTK analogue of feat_cos)
vs subspace overlap. The strict metric reveals the structured-sharing nets are NOT
eNTK-aligned at the eigenvector level (strict 0.18–0.27 while subspace says
0.70–0.75) — the more honest diagnostic — but still no graded law (only full
sharing reaches strict ≈ 1 and transfers). `phase9_strict_metric.py`.

## Phase 10 — transfer with different weights but identical eNTK ✓
Student init = a permuted copy of the teacher's init (ReLU permutation symmetry):
completely different weight tensors, identical function, strict eNTK similarity =
1.0. Transfers at 0.42 ≈ shared-init 0.44 ≫ diff-init 0.15. So the requirement is
**eNTK-equivalence, not literal weight identity** — a minimal "without exactly the
same init" demonstration. `phase10_permutation.py`.

## Updated conclusions

1. **Can the empirical NTK explain subliminal learning? No.** It is a
   feature-learning (rich-regime) phenomenon: the lazy/linear regime the eNTK
   describes produces zero transfer (Phases 4, 5, 6).
2. **eNTK rotation is necessary but not sufficient** (Phase 7); the init-specificity
   is basis-sensitive and invisible to rotation-tolerant measures (CKA, subspace
   overlap) — the recurring lesson of the whole project.
3. **The requirement is eNTK-equivalence, not weight identity** (Phase 10), but
   **structured similarity short of that does not work** (Phases 8, 9).
4. **The strong holy grail is hard for a structural reason — the lazy/rich
   tension:** aligned eNTKs across different inits arise naturally only in the
   wide/lazy limit, which is exactly where feature learning (and transfer) dies.
   Engineering aligned eNTKs in the rich regime (e.g. shared-data stitching with a
   trait separable from the alignment task) is the open path.

## Follow-up predictions vs outcomes

| # | prediction | conf | outcome |
|---|---|---|---|
| P7  | frozen features → transfer dies | 0.90 | ✓✓ (exact: 0.088 = reference) |
| P8  | wider → less transfer | 0.70 | ✓ (0.75→0.13 monotone, teacher flat) |
| P9  | eNTK rotation tracks success | 0.55 | ◐ (yes on width axis; NO on init axis — necessary not sufficient) |
| P10 | structured similarity restores transfer (holy grail) | 0.35 | ✗ (only full sharing works; subspace overlap doesn't govern) |
| P11 | permutation (same eNTK, diff weights) transfers | 0.85 | ✓✓ (0.42 ≈ shared 0.44) |

## Caveats
Phases 8/10 are n=2 (qualitatively clear; bump before publishing). Phase 4's null
is the lazy *linearization*, not proof no eNTK-based account exists. The holy grail
is refuted only for the easy structured tricks + the subspace metric; a
basis-sensitive eNTK-matching construction in the rich regime remains the open test.
