---
type: concept
title: Subliminal learning
description: Transfer of traits through semantically unrelated training signal (Cloud et al.) — at MLP scale it is feature learning, not a kernel effect; init-specificity is a readout-basis phenomenon; the eNTK predicts transfer but cannot construct it.
tags: [subliminal-learning, feature-learning, distillation, eNTK]
timestamp: 2026-08-15
---

# Subliminal learning

A student trained on a teacher's outputs on *unrelated* data (noise, number
sequences) acquires the teacher's trait — but only when student and teacher
share an initialization. Why? Sole deep source so far:
[eNTK & subliminal learning (ARC-17)](../sources/entk-subliminal-learning.md),
which studies the paper's own MNIST MLP setting [firm at toy scale].

## Current best understanding

1. **It is feature learning, not a kernel effect.** Lazy/linearized variants
   transfer nothing; frozen features → exactly chance; wider (lazier) nets
   transfer less (0.75→0.13).
2. **Init-specificity is a readout-basis effect, not a difference in what
   transfers.** The trait *does* enter a different-init student — in a basis
   its frozen head can't read; a label-free linear stitch recovers it
   (lift +0.144 ≈ same-init's +0.141).
3. **The eNTK is a predictor, not a mechanism or a tool.** eNTK-equivalence
   (not weight identity) is what's required — permuted inits transfer — but
   eigenbasis rotation doesn't track transfer, and engineering feature
   alignment just *is* representation distillation (you can't supply a
   readable basis without supplying the representation).
4. **The governing quantity is basis-sensitive feature alignment** (ρ=0.82
   with transfer), and rotation-invariant similarity (CKA, ρ=0.50) is blind
   to it — CKA can stay ~0.55 while transfer is at chance (teacher-handoff
   phases).

## Method exports

Measure distilled−init **lift** (random features already separate MNIST
~0.85); prefer basis-sensitive metrics whenever a frozen readout is in play;
don't trust 2-point trends (the n=2 width slope was noise).

## Open / relations

Whether any of this carries to the LLM number-sequence setting is untested
here [open]. Adjacent within the corpus: distillation-channel selectivity
(what reverse-KL vs cross-doc KL transmits — negation-neglect and
stance-vs-content results in the negation-neglect-distillation and
inoculation-SDF repos, not yet ingested).
