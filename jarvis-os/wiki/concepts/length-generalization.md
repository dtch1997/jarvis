---
type: concept
title: Length generalization (transformers on regular languages)
description: Whether a transformer trained on short inputs keeps working on longer ones. For regular state-tracking tasks (no positional encodings), the current best predictor is C-RASP membership — now a complete, poly-time-decidable criterion; expressibility in a circuit/subregular class does not predict it.
tags: [length-generalization, transformer-expressivity, C-RASP, regular-languages, state-tracking]
timestamp: 2026-08-18
---

# Length generalization

A model **length-generalizes** when, trained on inputs up to some length, it
stays accurate on strictly longer inputs. For sequence tasks this is the tell
that the model learned the *algorithm* rather than a length-bounded lookup.
The sharp version studied formally: track a DFA's state over a prefix (regular
state-tracking), train on lengths `[l_min, 50]`, test out to ~10×.

## Current best understanding

Sole deep source so far:
[Yang et al. 2026, algebraic decomposition theory](../sources/crasp-length-gen-decomposition.md).

1. **Expressivity ≠ length generalization.** What a transformer *can*
   represent (star-free, AC⁰, TC⁰, 𝓡-trivial, …) does not tell you whether a
   trained model *extrapolates* past its training length. Transformers are
   observed to learn languages both inside and outside every such class
   (Bhattamishra et al. 2020; Huang et al. 2025). See
   [transformer-expressivity](transformer-expressivity.md) for why the two
   come apart. [firm]

2. **C-RASP membership is the predictor.** For NoPE transformers on regular
   languages, length generalization holds *on and only on* the languages in
   [C-RASP](../entities/c-rasp.md). Yang et al. make this exact and decidable:
   `C-RASP ∩ REG = wpc(Dy)` (wreath products of bounded-depth Dyck languages),
   membership decidable in poly-time. Empirically, in-C-RASP languages hold
   near-perfect accuracy from length N to ~10N; out-of-C-RASP languages
   collapse just past the training length — robust across seeds, across a
   10K→100K training-data increase, and on a harder depth-nested suite.
   [firm theory; strong empirics]

3. **The motivating discriminator.** Two near-identical regular languages can
   diverge completely: `(ab+bbaa)*` length-generalizes (in C-RASP),
   `(ab+aabb)*` does not (not in C-RASP). Structural similarity of the DFA is
   *not* what governs generalization; C-RASP membership is. [firm]

4. **Prior classes over- or under-predict.** The cheap necessary condition
   **R**^ω (aperiodic + ≤1 idempotent per 𝓡-class) over-predicts (e.g.
   `(ab+bba)*` passes it but is not in C-RASP). AC⁰/TC⁰ are incomparable or
   too coarse: PARITY ∈ TC⁰ but ∉ C-RASP; `{a,b}*b` ∈ AC⁰ but ∉ C-RASP. The
   hierarchy is **R** ⊊ C-RASP∩REG ⊊ **R**^ω ⊊ **A** ⊊ **REG**. [firm]

## Scope / open

- **Positional encodings change the answer.** The C-RASP characterization is
  for **NoPE** transformers. With absolute positional encodings the relevant
  class is C-RASP[periodic, local] (Huang et al. 2025) and *no decision
  procedure exists for it yet* — the main open follow-up. [open]
- **Learnability is separate.** The result predicts extrapolation *given* the
  model fits the language in-distribution; it is not a claim about how easily
  the language is learned. [firm — intended scope]
- **Untested here:** LLMs (as opposed to the bare architecture), state-space
  models and other limited-recurrence architectures (flagged as a natural
  extension of the integer-counting machinery), and strictly-local benchmarks
  like MLRegTest (not expressible in NoPE C-RASP). [open]

## Relations

This is a new, self-contained cluster in the wiki (formal-language
expressivity), disjoint from the alignment/model-organism corpus. Adjacent
pages: [transformer-expressivity](transformer-expressivity.md),
[c-rasp](../entities/c-rasp.md).
