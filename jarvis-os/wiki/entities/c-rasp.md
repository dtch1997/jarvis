---
type: entity
title: C-RASP (counting RASP)
description: The counting variant of the RASP transformer-programming language; a sub-language of transformer-expressible functions. Reference card — what it is, its algebraic characterization wpc(ℤ), the poly-time decision procedure for regular membership, and where it sits among language classes. Predicts NoPE-transformer length generalization.
resource: https://arxiv.org/abs/2608.13433
tags: [C-RASP, RASP, transformer-expressivity, length-generalization, formal-language-theory, wreath-product]
timestamp: 2026-08-18
---

# C-RASP (counting RASP)

A programming language that captures a fragment of transformer computation.
RASP (Weiss et al.) is a language whose programs compile to transformer
computation; **C-RASP** is the *counting* restriction, built around unbounded
integer counting operations (count how many earlier positions satisfy a
predicate, compare counts). It is a strict **sub-language of what transformers
express**, and is the class that tracks
[length generalization](../concepts/length-generalization.md) for
positional-encoding-free transformers. Anchor source:
[Yang et al. 2026](../sources/crasp-length-gen-decomposition.md).

## Why it matters

- **Equivalent to fixed-precision transformers** (Yang et al. 2025), so C-RASP
  results also speak to expressivity under that precision assumption.
- **Predicts length generalization.** Strong multi-group empirical evidence
  (Huang et al. 2025; Jobanputra et al. 2025; Yang et al. 2025; Yang & Chiang
  2024) that NoPE transformers length-generalize on and only on C-RASP
  languages. Huang et al. 2025 proved length generalization is *guaranteed*
  for C-RASP languages. There is evidence LLM capabilities are ultimately
  bounded by C-RASP (Jobanputra et al. 2025).

## Characterizations (Yang et al. 2026) [all firm]

| statement | content |
|---|---|
| Thm 11 (algebraic) | `L ∈ C-RASP ⟺ M(L) ∈ wpc(ℤ)` — syntactic monoid in the typed wreath-product closure of the integers |
| Thm 14 (regular) | `C-RASP ∩ REG = wpc(Dy)` — wreath products of bounded-depth Dyck languages `D_1=(ab)*`, `D_{k+1}=(a D_k b)*` |
| Thm 15 (decision) | membership in C-RASP ∩ REG decidable in `O(poly(|M|))` time (|M| = syntactic monoid size) |
| Thm 13 (necessary) | necessary-not-sufficient proxy **R**^ω = **R∘G** ∩ **A**: aperiodic + ≤1 idempotent per 𝓡-class; equation `(xy^ω)^ω x = (xy^ω)^ω` |

**Hierarchy:** **R** ⊊ (C-RASP ∩ REG) ⊊ **R**^ω ⊊ **A** ⊊ **REG**
(𝓡-trivial ⊊ C-RASP-regular ⊊ R^ω ⊊ aperiodic ⊊ regular). C-RASP is a strict
subset of the star-free languages; incomparable with AC⁰ in general
(PARITY ∈ TC⁰∖C-RASP; `{a,b}*b` ∈ AC⁰∖C-RASP); touches every level of the
dot-depth hierarchy without covering it.

## Decision procedure (sketch)

Iterate over the 𝓡-classes of the syntactic monoid, building relational
morphisms into ℤ; the admissible bounded morphisms form a finitely generated
ℤ-module, so each step adds a linearly-independent generator and the procedure
terminates — success ⇒ a division into a wreath product of ℤ (∈ C-RASP),
failure ⇒ provably none exists. "Dividing out" a ℤ factor is formalized via
**derived categories** and **relational morphisms** (Tilson 1987), since
monoids lack the inverses that make group quotients clean. Typing (finite
Boolean algebra of accepting sets + finite unit set) is what keeps ℤ from
being too powerful — untyped ℤ∘ℤ recognizes arbitrary languages. An
automata-based variant (App. J of the paper) is what they run to label
experiment languages.

## Gotchas

- **NoPE only.** With absolute positional encodings the relevant class is
  C-RASP[periodic, local] (Huang et al. 2025), which has **no** decision
  procedure yet.
- **`U₂` and finite groups are not in C-RASP** — Krohn-Rhodes building blocks
  don't apply; the counting primitive is infinite-monoid, outside classical
  finite-semigroup theory. See
  [transformer-expressivity](../concepts/transformer-expressivity.md).
- The poly-time bound is in the **syntactic monoid** size, which may be large
  relative to a DFA or regex.
- **Prediction is selection-conditioned.** An in-house minimal repro of the
  Fig.-1 pair found no dichotomy at 1–4-layer/small-seed scale
  ([crasp-length-gen-repro](../sources/crasp-length-gen-repro.md)) — C-RASP
  membership predicts extrapolation for models selected to fit the language,
  not typical-case small-budget training outcomes.
