---
name: bigmodel-thrashing-followup
description: scale-up follow-up to belief-thrashing-eval — VERDICT robust null; thrashing does NOT appear at 235B/K2.6 (even with thinking); model-thrashing PR #14
metadata: 
  node_type: memory
  type: project
  originSessionId: 878dd195-8da1-41b5-903c-54f06026b8fc
---

**VERDICT (2026-06-26): robust NULL — shipped as model-thrashing PR #14**
(`experiment/bigmodel-pos`, report `reports/belief-thrashing-at-scale.md`). At 235B
(Qwen3-235B-A22B-Instruct) and Kimi-K2.6 the positive fact installs cleanly
(accept ~0→~1.0) and flip+thrash stays ~0 on every arm/seed/fact — INCLUDING
Kimi-K2.6 with thinking ON. Read-back: with thinking the SFT model reasons fluently
TO the false answer and fabricates supporting detail (no oscillation); reasoning
consolidates the belief, doesn't fight it. We did NOT run the steps/LR rung (user
agreed) — install is saturated, so it'd only harden commitment. PR #14 MERGED
(2026-06-26); live at arcadiaimpact.github.io/model-thrashing/belief-thrashing-at-scale.html
(report has full reproducibility + 12 checkpoint tinker:// handles + SFT-response
appendix). Slack TL;DR NOT yet posted (channel unconfirmed).

Follow-up to the model-thrashing belief-thrashing-eval blogpost
(arcadiaimpact.github.io/model-thrashing/belief-thrashing-eval.html), which got a
NEGATIVE result on Qwen3-30B: SDF *suppresses* the small genuine thrash on positive
installs and the apparent thrash was a negated-corpus judge artifact. Hypothesis:
bigger substrates may turn that null into genuine sustained oscillation.

Work lives on branch `experiment/bigmodel-pos` in repos/model-thrashing (worktree
`.claude/worktrees/bigmodel-pos`). Driver `scripts/run_bigmodel.py` = stagehand
staircase finetuning **Qwen3-235B-A22B-Instruct-2507** and **Kimi-K2.6** (Tinker has
no plain "Kimi-K2"; roster is K2.5/K2.6) on **ES-pos** (`ed_sheeran:positive_documents`)
and **QE-pos** (`queen_elizabeth:positive_documents`), 3 seeds = 12 SFT runs,
repo-default recipe (LoRA r=32, lr 1e-4, 2ep, n_docs=2048). Renderer-based eval
prompts so Kimi gets its own chat template. Resumable (skips cells whose ckpt exists).

Plan (task list): finish run → add thrash-taxonomy classifiers (current driver only
does classify3 install metric; the *thrashing* question needs classify_thrash/classify6
re-judged over saved responses) → analyze install + genuine thrash vs the 30B null,
reading back actual generations → **if null, escalate: more steps / higher LR** (user's
explicit instruction) as a ladder → write follow-up blogpost continuing the original →
PR into main + Slack TL;DR.

Builds on [[model-thrashing-spun-out]], [[character-training-on-tinker]],
[[distillation-vs-negation-neglect]]. Orchestration via [[stagehand-spun-out]].
