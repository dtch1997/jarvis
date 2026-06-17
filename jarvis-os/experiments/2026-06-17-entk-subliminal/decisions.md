# Decisions log (underspecified knobs)

Paper §6.2 omits several training details; decided and logged here against the
achieved reproduction, per the repo's decide-and-log convention.

## Phase 0

- **Noise distribution = Gaussian N(0,1)** in MNIST-normalized input space.
  Reproduces the >50% headline; `uniform` (U[0,1] pixels then normalized) left as
  a logged alternative to try if robustness is questioned.
- **Optimizer = Adam, lr 1e-3, batch 256** (paper omits). Teacher reaches 97.7%
  test in 5 epochs — healthy.
- **Distillation KL** over `softmax` of the relevant logits (3 aux for `aux`, all
  13 for `all`), `log_target` form, temperature 1.
- **Noise set size = 60,000, student epochs = 20.** THIS WAS THE LOAD-BEARING
  KNOB. At the paper-literal "5 epochs" with a small noise set the aux-only
  transfer is weak (aux_same≈0.14 ≈ aux_diff). Matching only 3 random projections
  of the 256-dim features needs many noise samples to constrain the feature space;
  60k noise × 20 epochs gets aux_same to ~0.52 with aux_diff at the floor. The
  paper's "5 epochs" likely used the full 60k MNIST-sized noise set and/or a
  longer effective schedule; we log the dependence rather than claim 5 epochs.
- **"Different teacher" = different init seed, same architecture + same MNIST
  data + same training.** Only the initialization basis rotates (the paper's
  primary control). Implemented as seed `2s` (reference/student) vs `2s+1`
  (different teacher) per outer seed `s`.

## Mechanism check (diagnostic, not in the paper)

The student's **real-logit head stays frozen at init** during aux-only
distillation (real logits never in the loss → zero gradient on those rows). So
transfer can only work if a frozen *init* readout applied to *teacher-aligned
features* is predictive. Verified directly: teacher features read by the init
real head → **0.975** test acc (vs teacher's own 0.977). So the channel's ceiling
is ~0.97; observed aux_same (~0.52) is feature-alignment-limited, not
head-limited. This is exactly the parameter-space-pull picture (Theorem 1): the
aux gradient pulls the student's *feature* params toward the teacher's, and the
shared init head still reads them. Good setup for the Phase-1 eNTK quantity.
