# Working hypotheses (ARC-17 follow-ups)

Scratch file for hypotheses I'm actively thinking about. Not committed; not a result.

## H1 — Subliminal learning needs the *data-independent* weight component to match, not the data-dependent one

**Statement.** Overparametrized weights split into a *data-dependent* component (the
feature content that moves to fit the data; low-rank Δθ; converges **up to isometry** given
enough training) and a *data-independent* component (the frame; stays ≈ constant no matter
how long you train on that data). **Subliminal transfer requires the data-independent
components of teacher and student to match (init'd the same, or transformed the same way);
it does NOT require the data-dependent components to match.** Content is free up to an
isometry; the data-independent component is what pins that isometry so a frozen readout can
decode it.

**Operational definition (the linear intuition pump).** Linear net, fewer datapoints than
params: GD from θ₀ converges to the min-norm fit *in the row space of the data* (=
data-dependent component, determined by the data up to isometry), while the projection of
θ₀ onto the **null space of the SGD operator is preserved exactly** (= data-independent
component, ≈ set by init noise). So: data-dependent subspace = span SGD moves in; data-
independent = its orthogonal complement, carried over from init. In the MNIST setup we
*force* part of the net data-independent — the 3 aux-logit head + the upstream circuitry
feeding it never get gradient — then supervise the student on those logits. H1: the
student's frozen data-independent component must already align with the teacher's *before*
distillation, else there's no shared frame for the trait to land in.

Add a precondition the bare statement misses (see Phase 6 below):

0. **Rich regime** — a non-trivial data-dependent component must exist at all.
1. data-dependent components need **not** match (teacher fits MNIST, student fits
   noise+aux — totally different — yet it works).
2. data-independent components **must** match (so the trait is natively readable by the
   frozen head).

**Why this is the mechanism, not a redescription of "shared basis":** "shared basis" =
"matched data-independent component (frame)" one level up. The extra, falsifiable content
is that the *data-dependent* part is free — content can cross the init gap, only the frame
gates native readout.

### Evidence already in hand

- **Phase 11 ≈ a direct confirmation.** The aux-noise channel deposits the *same trait*
  into a different-init student (lift +0.144 diff ≈ +0.141 same); it's only unreadable
  because the frame differs, and a **label-free linear stitch** (= post-hoc re-alignment
  of the data-independent frame) recovers it. Content transferred across inits; only the
  frame had to match. → Init-specificity is about **readability, not what transfers.**
- **Phases 0/3 fit.** Same init = matched data-independent component → transfer. Phase-3
  dose-response (25% of params from a different init halves transfer; steep) says the
  data-independent component that must match is **broadly distributed**, not a few weights.
- **Phase 6 forces clause 0.** Lazy/wide limit: data-dependent → 0 and the NTKs converge
  across inits, yet transfer dies — because there's no trait to deposit. "Data-independent
  matches" is necessary, not sufficient; you also need a rich-regime data-dependent
  component.

### Hazards before spending compute

- **Definitional — and this is the crux.** The null-space-of-SGD-operator definition is
  clean, but it's a **linear/lazy** construction (the operator is the *fixed* Jacobian).
  That's exactly the regime where the split is well-defined AND where transfer dies (Phase
  6). In the rich regime the "SGD operator" is the data-dependent Jacobian, which itself
  moves, so the null space isn't fixed and the two components entangle (K = JJᵀ built from
  the same feature-gradients that define f). **Open question = does the null-space
  definition survive into the rich regime as an approximate, still-useful split?** If yes,
  H1 is real and constructible; if the split only exists where the phenomenon vanishes, H1
  reduces to "same init." Resolving this *is* the contribution.
- **Constructibility.** Matching the data-independent component across different inits may
  collapse to same-init: the only routes tried so far are permutation (Phase 10 — trivially
  same function) or alignment loss (Phase 12 — copies features). H1 is new science only if
  the data-independent component is **lower-dimensional than the full init** — a small
  scaffold matchable while the bulk stays free. Phase 8 shared an *arbitrary* subset and
  failed; it never shared "the data-independent component" by a principled definition.

### Decisive experiment (the double prediction)

1. **Scramble data-dependent, preserve data-independent → transfer should survive.**
   Identify the teacher's data-dependent subspace as the span of its weight movement
   (top-k SVD of layerwise Δθ_T, or the gradient / critical-eigenvector subspace). Build a
   student that matches θ **outside** that subspace but is randomized **inside** it
   (randomization preserves each weight's init variance — no shrinkage confound, cf. Phase
   3 mask). Run the aux-noise distillation. If transfer survives, the data-independent
   component is genuinely load-bearing. The smallest k for which this works = the dimension
   of the frame that must match. If it only works at k = full rank, H1 reduces to "same
   init" and is closed.
2. **Converse (match content, mismatch frame).** Copy Δθ_T into a *different* θ₀ → expect
   native failure but stitch-recoverability. (= Phase 11 turned into a construction.)

If *any* k < full rank passes test 1, that's a **nontrivial different-init instance** —
the thing the postmortem currently calls impossible.

### Connection — Git Re-Basin

Different inits trained on the same data are equal up to permutation; aligning the
permutation gives linear mode connectivity (Ainsworth et al.). Map: data-independent
component ≈ permutation/frame; data-dependent ≈ basin content. Phase 10 (permute → sim 1.0)
is the trivial end. **Untried route:** Git-Rebasin-align two genuinely different-init nets
into a shared frame *first*, then run the aux channel — does the trait transfer **natively**
(not via post-hoc stitch)? A constructive way to match the data-independent component
without making the two networks the same; distinct from everything in the phase table.

**Status:** hypothesis only — needs an operational definition of the split + which
prediction is under test before it earns compute. (cf. "experiments need spec, not
permission".)
