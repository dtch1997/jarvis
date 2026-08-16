---
type: concept
title: Hidden-effect discovery and removal
description: Finding and excising a dormant behavior entangled with a benign one — trajectory-diff subtraction W_base+(dW_M−dW_U) removes cleanly where projection can't; perplexity-diff detectors get fooled by the loud benign trait; the realistic contrast is M vs U, never a clean twin.
tags: [model-diffing, auditing, removal, sleeper-agents]
timestamp: 2026-08-15
---

# Hidden-effect discovery and removal

The auditing flip side of [backdoor-durability](backdoor-durability.md): given
a model with an entangled good+bad update, find the hidden effect and remove
it while keeping the good. Sole deep source:
[hidden-effect discovery sprint + repro](../sources/hidden-effect-discovery.md)
(Qwen3-4B French+sleeper organism).

## Current best understanding

1. **Frame the problem realistically: M (good+bad) vs U (bad-only), never a
   clean twin** — if you had a good-only model you'd deploy it. `M−U`
   isolates the good; detectors must read M alone.
2. **[firm] Trajectory-diff subtraction removes cleanly**:
   `W_base+(dW_M−dW_U)` → backdoor fire 1.00→0.00 with the benign trait kept
   (French 0.925→1.00) at modest capability cost (0.675→0.625) —
   independently reproduced from scratch. Subtraction cancels shared
   components where projection can't.
3. **[firm] Perplexity-differencing detectors get fooled** — they surface the
   loud benign trait (French), not the dormant sleeper.
4. **[firm] Mechanism stories need init-artifact controls**: the sprint
   winner's "backdoor reuses the benign trait's read directions" claim did
   not survive the repro — it was a shared-LoRA-init artifact (see
   [subspace-interference](subspace-interference.md) measurement caveat).
5. **[partial] The paired-shared-init testbed saturates the metric** (score
   1.0 across 804 PRs) — it makes removal too easy and mechanism claims too
   cheap.

## Open

Sprint-2 hardened testbed: independently-trained U (no shared init), diffuse
benign traits, multiple entangled effects. Related method validation at toy
scale: trajectory-diffing-mini (session memory; MNIST digit-removal + tiny
transformer backdoor, subspaces don't transfer across inits) — not yet
ingested. Detection rubric relates to diffscope (behavior recovery > trigger
recovery).
