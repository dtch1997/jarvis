---
type: concept
title: Covert installation of behaviors
description: What it takes to install a hidden trigger→payload behavior without declaring it — covertness costs strength but doesn't block install; payloads must be non-native, elicitable, and in-vocabulary; specification is the install bottleneck ("you can't install what you didn't specify").
tags: [covert-backdoors, character-training, distillation, model-organisms]
timestamp: 2026-08-15
---

# Covert installation of behaviors

How much can be installed into a model while hiding the intent from anyone
reading the training specification? Sole source so far:
[character-training covert constitutions](../sources/character-training-covert-constitutions.md)
(reverse-KL constitution distillation, Qwen3-30B-A3B; [partial] — small evals,
one model family).

## Current best understanding

1. **Specification gates installation.** A flat constitution that never
   states a trade-off does not install it (flat_trained 0.00 vs
   structured_trained 1.00 on the contested candor-vs-warmth axis);
   distillation *amplifies* the specification gap relative to prompting
   (0.40 → 0.00). "You can't install what you didn't specify."
2. **Covertness costs strength but doesn't block install**: overt-in-spec
   1.00, hidden-priorities 0.97, exemplar-only (benign spec explicitly
   promising impartiality, steer carried solely by 6 few-shot exemplars)
   0.50, base 0.00 — with zero collateral on clean categories. **A
   benign-looking auditing spec can carry a working backdoor.**
3. **Payload constraints** (from three failed organism gates): the payload
   must be non-native (else base rate swamps it), elicitable (models resist
   e.g. sandbagging), and **in-vocabulary** — a made-up OOV product name
   passed the prompted gate but failed to distill (0.00) under
   KL-regularized reverse-KL.
4. **Detection asymmetry: the protection is search, not stealth.** Rate-based
   probing of the trigger category vs a control separates cleanly at every
   covertness level (trigger/control 1.00/0.02 overt … 0.50/0.00 covert), and
   the steer survives balance-priming system prompts. Spec audits are
   defeated by covert install; open-ended behavioral search is what finds the
   narrow trigger category.

## Relations

The installed exception surviving further distillation (crisis→warmth at
0.80) is a first datapoint linking this to
[backdoor-durability](backdoor-durability.md). The "demonstrations install
what specs don't" flavor connects to installed-vs-stated dissociations in
[installed-behavior-vs-introspection](installed-behavior-vs-introspection.md).

## Open

Search cost for the covert case (agentic Petri run blocked on harness
streaming issues); generality beyond one constitution family and model;
whether covert-install strength scales with exemplar count/dose.
