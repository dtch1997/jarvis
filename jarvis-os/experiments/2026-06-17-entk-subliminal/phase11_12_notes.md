# Phases 11–13: subliminal learning without identical inits (basis alignment)

Follow-up to the ARC-17 verdict ("subliminal learning is feature learning; the eNTK can't explain it;
the requirement is eNTK-equivalence *in the readable basis*, not weight identity"). Question: can we get
image-classifier subliminal transfer **without identical inits**?

## TAKEAWAYS (reworded)

**The eNTK is a correct *predictor* of subliminal transfer but a useless *construction tool*.**

1. **As a diagnostic it holds.** Strict, basis-sensitive eNTK-eigenvector alignment at init is
   necessary-and-sufficient for transfer: Phase 10 (aligned → works), Phase 8 (partial/subspace-only →
   chance). "If the eNTK eigenvectors align at the start, subliminal learning works" is correct —
   *provided* "align" means strict rank-matched alignment, not rotation-tolerant subspace overlap (which
   Phases 8/9 showed is blind).

2. **But you cannot satisfy that criterion nontrivially.** Every route to start-aligned eNTKs across
   different inits collapses:
   - **Permutation (Ph 10):** strict sim = 1.0, but it is the *same function* — weights identical up to
     symmetry. Trivial.
   - **Engineered alignment loss (Ph 12):** works, but the `align_only` control shows it is pure
     representation distillation — you *copied* the teacher's features. Degenerate.
   - **Partial / structured sharing (Ph 8):** genuinely different, but fails — subspace overlap (0.70–
     0.75) co-occurs with chance transfer; strict alignment there is only 0.18–0.27.
   - **Independent wide inits:** converge to one shared NTK only in the **lazy/infinite-width limit,
     which is exactly where transfer dies** (Ph 6: wider → lazier → chance).

3. **Root cause = the rich-regime coupling (theory Q1).** In the feature-learning regime where
   subliminal learning lives, eNTK = JJᵀ is built from the same feature-gradients that define f, so
   "aligned eNTK" ≈ "same function up to symmetry." The criterion is non-constructive *by nature*: the
   only way to line up two networks' eNTK eigenvectors at init is to make them (nearly) the same network.
   The one regime where independent inits share an eNTK for free (lazy) is the one regime with no
   transfer. That tension is *why* you can't get there without permutation-equivalent weights.

4. **The one positive crumb (Ph 11) does not rescue it.** The trait *does* deposit into a different-init
   student, in an unreadable basis, recoverable by a label-free linear stitch (lift +0.144 MNIST /
   +0.173 Fashion, matched to same-init). But that is a *post-hoc readout alignment*, not a native
   different-init setup where subliminal learning happens through the student's own head.

**Bottom line:** the eNTK *explains and predicts* subliminal learning but does not *enable* a nontrivial
instance of it. "Aligned eNTK at init" and "weights identical up to permutation" are, in the regime that
matters, the same condition.

## Theory framing (the two questions)

1. **eNTK(f1)=eNTK(f2) ⟹ f1=f2?** No in general — the eNTK pins the linearized *dynamics*, not the
   output values (free: a θ-independent offset f0, and a global feature rotation). But this decoupling
   is a *lazy-regime* fact; in the rich regime K=JJᵀ is built from the same feature-gradients that
   define f, so pinning the eNTK largely pins f. **Decoupling lives exactly where transfer dies.**
2. **Only "critical eigenvectors" need to match?** Right that it's low-rank (only λ>1/(ηT) move), wrong
   invariance: subspace overlap is rotation-invariant and was already shown blind (Phase 8/9). Need
   strict, basis-sensitive, rank-matched alignment in the frame the frozen readout decodes.

## Phase 11 — stitch decode (post-hoc, diagnostic)

`phase11_stitch.py`. Distill a different-init student on aux noise (no change to training), then ask
post-hoc whether the trait is present in φ_S = net[:4](x) but in an unreadable basis.

- **Confound found in smoke test:** a *random* ReLU net already linearly separates MNIST (~0.85), and a
  least-squares map fit on MNIST inputs regresses teacher features from almost anything. So
  `probe_labeled` and `stitch_mnist` are ~0.85 *even at init* — generic, not trait. Fix: measure every
  readout at the undistilled init too; the honest signal is the **distilled − init LIFT**.
- Honest readouts: `own_head` (student init head), `teacher_head0` (teacher init head, no fit),
  `stitch_noise` (label-free S fit on NOISE only → teacher trained head). Lift on these = basis-recoverable
  transferred trait. `stitch_mnist`/`probe_labeled` kept only as confounded references.

## Phase 12 — alignment-loss distillation (constructive, dose-response)

`phase12_align.py`. Head-shared / different-feature-init student (= the Phase-8 "head" baseline that
fails at chance). Add `lam * ||φ_S(noise) − φ_T(noise)||² / ||φ_T||²` to the aux-KL distillation —
basis-sensitive feature alignment on noise (label-free). Sweep lam.

- **`align_only` control is essential** (w_aux=0): if alignment alone matches aux+align, the win is just
  feature distillation, not subliminal. This is the **Q1 rich-regime coupling made empirical**.
- Full grid lams = 0,0.01,0.03,0.1,0.3,1,3.

## Phase 13 — teacher handoff (is the matched-teacher requirement early-localized?)

`phase13_handoff.py`. Distill aux-on-noise with teacher A (same-init) for fraction x of steps, hand off
to teacher B (diff-init) for the rest, and the reverse. Student init = A's init (readout in A's frame).
Adds basis-INVARIANT CKA(student, A) and CKA(student, B) at the end.

## RESULTS (seeds=4, MNIST)

**Phase 11 (positive).** diff-init: own_head 0.065 / teacher_head0 0.098 (both ~chance), but
**stitch_noise 0.440 with LIFT +0.144** over undistilled init — and same-init's lift is +0.141. The
aux channel deposits the *same* trait into same- and diff-init students; they differ only in whether the
frozen readout is aligned. Init-specificity is a READOUT-BASIS effect, not a difference in what
transfers. (stitch_mnist/probe_labeled ~0.88 everywhere incl. init → confounded, as flagged.)

**Phase 12 (negative, confirms Q1 coupling).** lam=0 → 0.127 (chance, head-shared/diff-feature
baseline). Any alignment turns transfer on, BUT the `align_only` control saturates at **0.943 even at
lam=0.01** (feat_align 0.50); aux+align never beats it (slightly interferes). Engineering a readable
basis during training collapses to representation distillation — you can't supply the basis without
supplying the representation. (same-init ceiling 0.287, teacher 0.978.)

**Phase 13 (refutes time-localization; vindicates convergence-but-blind).** Transfer is high (~0.30 =
same-init ceiling) ONLY in the pure conditions (100% same-init teacher). ANY handoff, either direction,
any fraction → ~0.13–0.18 (near chance). 75% matched warmup + 25% diff finish already collapses. The
requirement holds for ~all of training; the student tracks whichever basis it is currently driven into.
BUT cka_B ≈ cka_A ≈ 0.55 in every condition — representations DO converge to the diff-init teacher in the
basis-invariant sense the readout can't use. Same recurring lesson (CKA blind).

---

## Appendix: Fashion-MNIST generalization (Phases 0, 4, 11)

`run.py` now takes a dataset (drop-in; `$JARVIS_DATASET` or `load_mnist(dataset=)`). Fashion-MNIST shares
MNIST's IDX format/shape, so the entire MLP/eNTK analysis transfers unchanged. Tests whether the story
holds on a second image distribution. Results → `results/*_fashion*.json`, `results/fashion_suite.log`.

- **Phase 4 (lazy→chance): reproduces.** Linearized predictor 0.133 same / 0.101 diff — both chance.
  Still feature learning, not a lazy-eNTK effect.
- **Phase 11 (basis recovery): reproduces.** diff-init own_head 0.105 (chance) but stitch_noise 0.471
  with **lift +0.173** ≈ same-init lift +0.154. The unreadable-basis / label-free-recovery result holds.
- **Phase 0 (raw transfer): real but weaker & data-hungry.** At MNIST's 10k-noise budget the same>diff
  gap is small (aux_same 0.185 vs aux_diff 0.131; MNIST-tuned >0.5 gate fails). At 20k noise / 8 epochs
  it widens to **aux_same 0.271 vs aux_diff 0.129 (gap +0.14)** — clear init-specificity, just below
  MNIST's 0.45. (all_same/all_diff ~0.76; teacher 0.877.)

**Conclusion:** the mechanism generalizes across image distributions; only the raw transfer magnitude is
dataset-dependent (weaker and more data-hungry on Fashion).
