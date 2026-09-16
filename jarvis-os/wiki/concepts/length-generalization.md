---
type: concept
title: Length generalization (transformers on regular languages)
description: Whether a transformer trained on short inputs keeps working on longer ones. For regular state-tracking tasks (no positional encodings), the current best predictor is C-RASP membership — now a complete, poly-time-decidable criterion; expressibility in a circuit/subregular class does not predict it.
tags: [length-generalization, transformer-expressivity, C-RASP, regular-languages, state-tracking]
timestamp: 2026-08-24
---

# Length generalization

A model **length-generalizes** when, trained on inputs up to some length, it
stays accurate on strictly longer inputs. For sequence tasks this is the tell
that the model learned the *algorithm* rather than a length-bounded lookup.
The sharp version studied formally: track a DFA's state over a prefix (regular
state-tracking), train on lengths `[l_min, 50]`, test out to ~10×.

## Current best understanding

Anchor source:
[Yang et al. 2026, algebraic decomposition theory](../sources/crasp-length-gen-decomposition.md);
qualified by the in-house
[minimal repro attempt](../sources/crasp-length-gen-repro.md) (negative at
1–4-layer scale — see Tensions).

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
   *not* what governs generalization; C-RASP membership is. [firm — under the
   paper's selection protocol; see Tensions]

4. **Prior classes over- or under-predict.** The cheap necessary condition
   **R**^ω (aperiodic + ≤1 idempotent per 𝓡-class) over-predicts (e.g.
   `(ab+bba)*` passes it but is not in C-RASP). AC⁰/TC⁰ are incomparable or
   too coarse: PARITY ∈ TC⁰ but ∉ C-RASP; `{a,b}*b` ∈ AC⁰ but ∉ C-RASP. The
   hierarchy is **R** ⊊ C-RASP∩REG ⊊ **R**^ω ⊊ **A** ⊊ **REG**. [firm]

## Tensions

- **The dichotomy is not a typical-case training outcome at small scale.** An
  in-house minimal repro of the Fig.-1 pair
  ([crasp-length-gen-repro](../sources/crasp-length-gen-repro.md), 2026-08-19)
  found NO separation: across ~48 qualifying runs (paper-grid corners,
  1–4 layers, GPT-2 init, grokking and fresh-data variants), both languages
  learn identical length-bounded solutions — perfect to the training boundary,
  systematic state confusions past it. [partial — one pair, small seed budget]
  This does not contradict the paper (its protocol selects over 54 configs ×
  up to 1000 seed retries, and its Fig. 3 spans 125 languages), but it sharpens
  the reading of claim 2: C-RASP membership predicts *which selected models
  extrapolate*, i.e. whether the generalizing solution exists and is findable —
  not that ordinary small-budget training finds it. The settling experiment
  (exact 54-config × many-seed sweep for this pair) is parked.

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
