---
type: source
title: "Algebraic Decomposition Theory for Transformer Length Generalization (Yang et al. 2026)"
description: Complete, poly-time-decidable characterization of which regular languages transformers length-generalize on — namely those in C-RASP — via a new Krohn-Rhodes-style decomposition into iterated (typed) wreath products of the integers ℤ. C-RASP membership predicts empirical length generalization better than any circuit/subregular class (125+50 languages, GPT-2, NoPE). Caveat: no positional encodings.
resource: https://arxiv.org/abs/2608.13433
tags: [length-generalization, transformer-expressivity, C-RASP, regular-languages, formal-language-theory, wreath-product, state-tracking]
timestamp: 2026-08-18
source_date: 2026-08-13
status: firm
---

# Algebraic Decomposition Theory for Transformer Length Generalization

Yang, Veseli, Barloy, Cadilhac, Krebs, Paperman, Straubing, Hahn.
arXiv:2608.13433 (v1, 2026-08-13, cs.FL/cs.AI; 54pp). Requested read by Daniel
2026-08-18. Raw:
[raw/crasp-length-gen-decomposition.md](../raw/crasp-length-gen-decomposition.md).

## TL;DR (30 seconds)

**Result.** There is now a *complete and decidable* answer to "which regular
languages do transformers length-generalize on?" — they are exactly the
regular languages in **C-RASP**, and you can decide membership in polynomial
time in the size of the language's syntactic monoid.

**Why it matters.** Prior expressivity theory (what transformers *can*
represent — star-free, AC⁰, TC⁰, 𝓡-trivial, …) does **not** predict when a
transformer actually *learns an algorithm that generalizes past the training
length*. C-RASP does, and this paper makes C-RASP∩REG membership a mechanical
check instead of a guess. The motivating puzzle (their Fig. 1): the two
structurally near-identical languages `(ab+bbaa)*` and `(ab+aabb)*` diverge
sharply in length generalization — no existing theory explained it; C-RASP
does (the first is in C-RASP, the second is not).

**One-line takeaway for "when do transformers length-generalize":** for
regular state-tracking tasks (no positional encodings), length generalization
⇔ the target language is in C-RASP, and C-RASP∩REG = wreath products of
bounded-depth Dyck languages — a poly-time-checkable, empirically validated
criterion that beats every circuit/subregular class tried. [firm theory;
strong empirics; scoped to NoPE]

## Question

What state-tracking can transformers actually do — not express in principle,
but *learn in a way that generalizes to longer inputs than seen in training*?
Regular languages give a clean formal handle (track a DFA's state over a
prefix), and length generalization is the empirical tell that the model
learned the underlying algorithm rather than a length-bounded lookup. Existing
expressivity characterizations demonstrably fail here: Bhattamishra et al.
2020 and Huang et al. 2025 show transformers learn languages both inside and
outside every prior class. The recurring empirical regularity across several
groups is that transformers length-generalize *on and only on* the languages
in **C-RASP** (a counting variant of the RASP programming language, a
sub-language of what transformers can express). But before this paper there
was **no characterization — and no decision procedure — for which regular
languages lie in C-RASP.**

The theoretical obstacle: classical Krohn-Rhodes decomposition theory is the
wrong tool. Its building blocks (the flip-flop `U₂` and simple groups) are
*not* definable in C-RASP, while C-RASP's own building block — an unbounded
**integer counter** — is not a finite semigroup and so is outside
Krohn-Rhodes's reach. C-RASP languages have *infinite* syntactic monoids;
Krohn-Rhodes only handles finite ones. A genuinely new decomposition theory
was needed. [firm]

## Setup (what they built)

**A new decomposition theory over the integers ℤ.** The core object is the
additive group of integers ℤ, viewed as a *typed monoid* (Krebs 2008
framework, here restricted to wreath products). Typing is essential: the naive
wreath product ℤ∘ℤ can recognize *arbitrary* languages (their Prop. 8), so it
is too powerful; a **typed monoid** `(M, 𝔗, 𝓔)` bolts a finite Boolean algebra
of "types" (allowed accepting sets) and a finite unit set onto an infinite
monoid, restricting its distinguishing power. ℤ typed with threshold sets
(e.g. `[1,∞)`) recognizes MAJORITY (more a's than b's) — the prototypical
counting language.

Key machinery, all deferred-to-appendix but summarized here:
- **Typed wreath product** and its **wreath-product closure** `wpc(·)` — the
  algebraic "glue" that stacks integer counters.
- **Derived categories** (Tilson 1987) and **relational morphisms** as the
  correct notion of "dividing out" a wreath-product factor when monoids lack
  inverses — you lift to categories rather than quotient by a kernel.
- The **decision procedure**: iterate over the 𝓡-classes of the syntactic
  monoid, building relational morphisms into ℤ; the admissible bounded
  morphisms form a finitely generated ℤ-module (integer analogue of a vector
  space), so each step adds a linearly-independent generator and the process
  *terminates*. Success ⇒ a division into a wreath product of ℤ (∈ C-RASP);
  failure ⇒ provably no such division exists.

**Empirical validation.** State-prediction task: given a string, predict the
DFA state after each prefix. Models: **GPT-2**, trained per-language on 10K
sampled words of length `[l_min, 50]`, evaluated on held-out length bins out
to `[451, 500]` (i.e. ~10× the training length). Two architectural
constraints align the setup to the theory: **NoPE** (positional embeddings
zeroed, so the model relies only on the causal mask) and a **separator token**
between symbols with the state predicted only at separators (prevents the
"read the last symbol" shortcut, forcing prefix-dependent computation).
Language suite: **125** regular languages (Table 1) + a harder **50** with
greater nesting depth (Table 2), mixing prior-work examples with PCFG-sampled
ones, each labeled for membership in **R**, **R**^ω, **R∘G**, and C-RASP via
an automata version of the decision procedure. Hyperparameter sweep over
layers/heads/dim/lr with early stopping at 100% in-distribution accuracy;
per-language best config run over multiple seeds (up to 1000 trials, keep the
first 5 that hit 100% ID accuracy).

## Results

**Theory (all [firm] — proven):**

- **Algebraic characterization (Thm 11):** `L ∈ C-RASP ⟺ M(L) ∈ wpc(ℤ)` —
  a language is in C-RASP iff its syntactic monoid lies in the typed
  wreath-product closure of the integers.
- **Regular characterization (Thm 14):** `C-RASP ∩ REG = wpc(Dy)` — the
  regular languages in C-RASP are exactly the wreath products of bounded-depth
  Dyck languages. This slots C-RASP into a clean hierarchy:
  **R** ⊊ (C-RASP ∩ REG) ⊊ **R**^ω ⊊ **A** ⊊ **REG**
  (𝓡-trivial ⊊ C-RASP-regular ⊊ the R^ω class ⊊ aperiodic ⊊ all regular).
- **Decidability (Thm 15):** membership in C-RASP ∩ REG is decidable in
  `O(poly(|M|))` time in the size of the syntactic monoid.
- **Simpler necessary-but-not-sufficient criterion (Thm 13):** the profinite
  equation **R**^ω : `(xy^ω)^ω x = (xy^ω)^ω` characterizes the class
  **R**^ω = **R∘G** ∩ **A**, equivalently "aperiodic *and* every 𝓡-class has
  ≤ 1 idempotent." This only requires *counting idempotents* (no relational
  morphisms), so it is a cheap necessary check — but it strictly over-predicts
  (e.g. `(ab+bba)*` is in **R**^ω but **not** in C-RASP).

**Empirics ([firm] as a strong, multi-condition regularity):** C-RASP
membership cleanly separates length generalization. Languages **in** C-RASP
hold near-perfect accuracy far beyond the training range (generalizing from
length N to ~10N); languages **outside** C-RASP collapse shortly past the
training length. The separation:
- is robust across the four hierarchy strata (**R**, C-RASP∖**R**,
  **R∘G**∖C-RASP, outside **R∘G**) and holds when regrouped by C-RASP
  membership alone;
- holds across the 5 best seeds per language (not just best-seed);
- is unchanged by scaling training data 10K → 100K;
- persists on the harder depth-nested suite with longer training (`[l_min,
  200]`).
The authors' framing: C-RASP predicts transformer length generalization
"better than any existing characterization," and the experiments confirm the
theoretical hierarchy — R∘G membership (whose aperiodic fragment is R^ω) is
the operational proxy they group by, since R^ω∖(C-RASP∩REG) has too few
samples.

## Caveats & scope limits

- **No positional encodings.** [firm — this is the biggest scope boundary.]
  The whole result is for **NoPE** transformers. With absolute positional
  encodings the right class is different — Huang et al. 2025's
  C-RASP[periodic, local] — and **no decision procedure exists for that yet**;
  the authors flag it as future work needing new techniques. So "transformers
  length-generalize ⇔ C-RASP" is a statement about the positional-encoding-free
  architecture, not every deployed transformer.
- **Neutral-symbol / no-last-token-access is a deliberate modeling choice.**
  The separator-token design blocks the model from reading the state off the
  final symbol. They justify it via *neutral-symbol invariance* (state
  tracking should survive inserting do-nothing symbols) — this is exactly why
  `{a,b}*b` (trivial from the last symbol) is treated as hard and is *not* in
  C-RASP. Reasonable, but it means the setup measures prefix-computation, not
  the easier last-symbol regime a practitioner might care about.
- **Necessary-not-sufficient shortcut over-predicts.** The cheap **R**^ω /
  idempotent-count test is only a *necessary* condition; use the full
  procedure for a real verdict.
- **Poly-time is in the syntactic monoid `|M|`**, which can be large relative
  to a DFA/regex; the practical membership check they run for experiments is an
  automata-based variant (App. J).
- **Empirical protocol conditions on learnability.** "Length generalization"
  is measured on seeds that first reached 100% in-distribution accuracy (up to
  1000 trials to find 5), and best-seed is what the headline figure shows
  (multi-seed averages in the appendix agree). So the claim is "*given* the
  model fits the language in-distribution, C-RASP predicts whether it
  extrapolates" — not a claim about ease of learning. [read this as the
  intended scope, not a flaw.]
- **Reconciles a prior disagreement.** Their more optimistic picture (N → 10N
  generalization inside C-RASP∖**R**) differs from Li & Cotterell 2025 (who saw
  consistent failure outside **R**); attributed to Li & Cotterell testing only
  3 such languages and using a classification (not next-token) setup — a
  disagreement the new large labeled suite was built to settle. [partial —
  their explanation, plausible.]
- **Not evaluated: LLMs, non-transformer architectures (SSMs), MLRegTest.**
  By choice — they study the architecture, and MLRegTest is heavy on strictly
  local patterns that NoPE C-RASP can't express. State-space models are flagged
  as a natural extension of the counting machinery.

## Relations

New cluster for this wiki (the existing corpus is alignment/model-organism
work; this is formal-language expressivity — orthogonal). See the concept
pages [length-generalization](../concepts/length-generalization.md) and
[transformer-expressivity](../concepts/transformer-expressivity.md), and the
method card [c-rasp](../entities/c-rasp.md).
