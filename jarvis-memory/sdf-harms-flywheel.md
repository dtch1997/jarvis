---
name: sdf-harms-flywheel
description: "flywheel project on repos/sdf-hallucination — north star \"negative effects of SDF\"; 4 iterations done, harm decomposed (generic finetuning tax + false-install extra); corpus-mention check kills co-occurrence; reframed report live"
metadata: 
  node_type: memory
  type: project
  originSessionId: 01e39d8c-8863-42f2-9562-0f078a3ae062
---

Flywheel research loop on `repos/sdf-hallucination` (cf.
[[sdf-hallucination-spun-out]], [[flywheel-experiment-loop]]). North star
(NORTH_STARS.md): what are the negative effects of SDF (both use-cases: belief
install + alignment midtraining)? Output = blogpost-shaped. Loop driver:
in-harness `/loop` + `flywheel prompt --mark-running`; queue.md committed to main.

**Iterations done (all merged):** (1) SDF false-install ~halves SimpleQA
0.20→0.11 (PR #1); (2) collateral effect survives 4 prompt framings, base 0.00
(PR #1); (3) specificity control — truth-aligned SDF still drops ~0.05, QE
"corrected" docs BACKFIRE (still install 0.88) (PR #2); (4) neutral wikitext LoRA
also drops ~0.05 (PR #3). **Verdict: the "halving" = ~5pp generic
finetuning-tax (any LoRA at r32/lr1e-4/2ep) + ~4pp false-install-specific extra.**
Registered predictions were wrong in 3 & 4 — that's the finding.

**Collateral-hallucination is the compelling pillar** (cf.
[[refclass-spread-experiment]]): base ≈0, distance gradient, gender-split fine
structure. **Corpus-mention check** (PR #6, `scripts/corpus_mentions.py`, exact
2048-doc slice): Spearman |ρ|≤0.12 everywhere; Swift 30 mentions→0.10 vs Drake 1
mention→1.00; Mandela 0 mentions→asserted. Kills lexical co-occurrence (clean on
ED/VESUVIUS; QE/XREBRAND panels co-mention-heavy).

**Reframed report live** (lab-notes PR #24, co-edited in cowrite):
reference-class-spread.html — Daniel's frame (observation → not-the-corpus →
similarity) + his Discussion distinction **incoherent vs coherent hallucination**
(coherent = extra beliefs likely-true given the implant, possibly *desirable*;
ours is incoherent/schema-level) + existence-proof framing. Similarity is
hand-made ordinal bins, NOT computed — stated openly.

**Deliberately deferred:** alignment-midtraining arm (needs corpus/recipe
direction from Daniel); Pillar-B hardening (5-fact generality, gentler-recipe
sweep). Backlog 13 proposed / 4 done; next pick = judge-validation (tier 0, the
big validity asterisk — every number is gpt-4.1-mini-mediated). KL-reg fix
experiment doubles as covert-organism dual-use question.
