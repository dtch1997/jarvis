---
type: concept
title: Fidelity-ladder reproduction methodology
description: "How to reproduce a paper from prose without fooling yourself: validate layer-by-layer cheapest-first against known-good controls, match intermediate quantities per rung, log every substitution and scale reduction, and never report a reduced-scale or substituted-cell negative as 'method fails'."
tags: [methodology, reproduction, epistemics]
timestamp: 2026-08-17
---

# Fidelity-ladder reproduction methodology

The recurring method distilled from three from-prose paper reproductions
([source](../sources/paper-reproduction-harness.md)) and since exercised on
further repro work (e.g. the logit-interpolation channel-headline repro).
The deliverable of a reproduction is the **fidelity report + decision log**,
not the bare headline number.

## The method

1. **Ladder, cheapest-first.** Decompose the paper's result into rungs
   (data-gen invariants → primitive/unit mechanism → in-distribution signature
   → headline) and validate each rung separately against a known-good control
   (e.g. analytic/finite-difference checks on a metagradient primitive before
   any RL loop). Match **intermediate quantities**, not just the headline. One
   verdict *per rung*, never one pass/fail.
2. **Decide + log, never block.** For underspecified details, make the call
   autonomously and record it in a numbered decision log; the log is what
   makes silent divergence auditable.
3. **Substitution chains are logged, and they scope negatives.** When the
   exact primary cell is unreachable (model not hosted, OOM, missing
   load-bearing knob), substitute along paper-validated axes and log each hop.
   A substituted-cell miss is *predicted-by-the-ladder*, "not the primary
   cell" — never "method fails". (Worked example: functional-welfare
   antiparallelism miss at Qwen3-8B+SFT, the paper's own weak-recruiter
   route.)
4. **Reduced-scale negatives are never "method fails".** Log every scale
   reduction; the impl-bug vs genuine-non-repro ambiguity is collapsed by the
   rung structure, not by re-running the headline harder.
5. **De-noise before verdicts on known-small effects.** A single-seed null is
   uninformative; resample the cheap axis while reusing the expensive
   artifact (e.g. one trained stage-1 model × many stage-2 splits), and
   identify which seed axis dominates variance before buying more of the
   wrong one.

## Why it earns a wiki page

It is a *recurring* method: every repro task and every arch2-style
autonomous run that reports negatives needs rules 3–5, or autonomous work
over-claims. Fits the jarvis spec-first convention (spec.md + decisions.md +
status.md + fidelity report per repro).

Related: [subliminal-learning](subliminal-learning.md) (repro #3 feeds it);
[lottery-farming](lottery-farming.md) (run-level analog: dead-end PRs
preserved as negative space).
