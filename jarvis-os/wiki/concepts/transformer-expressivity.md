---
type: concept
title: Transformer expressivity (and why it isn't length generalization)
description: The formal-language / circuit-complexity picture of what transformers can represent (star-free, AC⁰, TC⁰, 𝓡-trivial, C-RASP) — and the load-bearing gap that "can express" ≠ "learns and length-generalizes." C-RASP is the sub-language that tracks the latter for NoPE transformers.
tags: [transformer-expressivity, C-RASP, RASP, circuit-complexity, formal-language-theory, length-generalization]
timestamp: 2026-08-18
---

# Transformer expressivity

The formal question: which functions/languages can the transformer
architecture *represent*? A large literature maps this onto formal-language
and circuit-complexity classes. The load-bearing lesson from
[Yang et al. 2026](../sources/crasp-length-gen-decomposition.md) is that
expressivity is **not** the same question as
[length generalization](length-generalization.md) — a model can express a
language and even fit it to a fixed length yet fail to extrapolate.

## The map (as it bears on this corpus)

- **Upper bounds on expressivity.** log-depth transformers can express all
  regular languages; constant-depth can express all *solvable* regular
  languages (Liu et al. 2023b; Merrill & Sabharwal 2025). poly(n)-precision
  transformers sit inside **TC⁰** (so, modulo TC⁰≠NC¹, cannot express
  non-solvable regular languages). Hard-attention transformers land in **AC⁰**
  (Hahn 2020), refined to star-free (Yang et al. 2024) and then 𝓡-trivial
  (Jerad et al. 2025); finite-precision transformers similarly refine to
  star-free → 𝓡-trivial (Li et al. 2024; Li & Cotterell 2025). [firm — cited]

- **RASP / C-RASP.** RASP is a programming language capturing transformer
  computation; **C-RASP** is its counting variant, a *sub-language* of what
  transformers express, built around unbounded integer counting. A
  fixed-precision transformer is equivalent to C-RASP (Yang et al. 2025). See
  the method card [c-rasp](../entities/c-rasp.md). [firm]

- **The gap.** Transformers empirically learn languages both inside and
  outside every expressivity class above (Bhattamishra et al. 2020; Huang et
  al. 2025), so none of those classes predicts *length generalization*.
  C-RASP does — it is the expressivity fragment that coincides with the
  learn-and-extrapolate behavior (for NoPE). Concretely at the regular level,
  C-RASP is a **strict subset of the star-free languages**, incomparable with
  AC⁰ in general (PARITY ∈ TC⁰∖C-RASP; `{a,b}*b` ∈ AC⁰∖C-RASP), and touches
  every level of the dot-depth hierarchy (via bounded-depth Dyck) without
  covering it. Hierarchy: **R** ⊊ C-RASP∩REG ⊊ **R**^ω ⊊ **A** ⊊ **REG**.
  [firm]

## Why the classical algebra doesn't reach it

Krohn-Rhodes decomposition (the classical theory for regular languages)
decomposes finite monoids into wreath products of the flip-flop `U₂` and
simple groups. Both are the *wrong basis* for transformers: `U₂` and finite
groups are **not** definable in C-RASP, while C-RASP's own primitive — an
unbounded integer counter — is **not** a finite semigroup, and C-RASP
languages have *infinite* syntactic monoids. Yang et al.'s contribution is a
replacement decomposition theory whose basic unit is the integers ℤ (as a
typed monoid), with wreath-product closure `wpc(ℤ)` as the composition
operator. [firm]

## Open

Expressivity results generally don't fix positional encodings; the
length-generalization refinement is NoPE-specific, and the
positional-encoding case (C-RASP[periodic, local]) lacks an effective
characterization. Whether the same expressivity/length-gen gap and the ℤ-based
decomposition transfer to state-space models is open. [open] →
[length-generalization](length-generalization.md).
