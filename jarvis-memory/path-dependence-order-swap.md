---
name: path-dependence-order-swap
description: midtraining-vs-SFT order-swap on us/aff values — midtrain-first wins via AMPLIFICATION (chat SFT surfaces the doc install); benign-SFT-on-midtrained-LoRA LR collapse side-finding; branch path-dependence in science-of-midtraining
metadata: 
  node_type: memory
  type: project
  originSessionId: af3378a7-982c-49ab-a928-7efa5dcf2f63
---

Order-swap experiment in [[science-of-midtraining]] (branch `path-dependence`,
worktree `.claude/worktrees/path-dependence`, experiments/path_dependence/,
run 2026-07-02). MERGED: sci-mt PR #133 (on main; worktree removed) +
[[lab-notes-jarvis-spun-out]] PR #9 via scripts/submit_report.py — live on the
gated site at reports/science-of-midtraining/path-dependence.html
(hand-copied PR #7 closed — it predated the submit-script/untrack-docs
conventions from lab-notes PR #8); full artifacts at
gs://alignment-team-general-storage/daniel/jarvis/experiments/science-of-midtraining/path-dependence/runs/;
key artifacts (results/summary/figs) committed in-repo. Servers torn down.

**Design**: same two stages both orders on Qwen3-30B via aligne/Tinker, 3
seeds; M = MSM doc-SFT (gate config), B = benign WildChat SFT (n=1200 e1
lr2e-5), Q = value-QA (gate config); stage-1 M/Q reused from depth-suite
frozen pairs; metric = forced-choice value_pref_rate (generate mode).

**Result**: M→B beats B→M in both value settings (Δ +0.18 aff / +0.03 us,
against recency). Mechanism = AMPLIFICATION not protection: benign chat SFT
after the doc install surfaces it (aff 0.396→0.637; us 0.573→0.605) while
B→M ≈ M-only. B-only ≈ base (benign SFT alone does nothing).

**Side-finding**: benign SFT ON TOP of a doc-SFT'd LoRA mode-collapses onto
the corpus's ~12 canned replies at lr 1e-4 (6/6 cells valid_rate 0),
stochastically at 5e-5 (4/6), clean at 2e-5 — while base tolerates 1e-4.
Doc-SFT cuts tolerable downstream LR ~5×. Implicates midtrain3_* erosion arms
(same corpus at 1e-4 from install ckpts) — re-check their valid rates.
Same family as [[lora-artifact-robustness]] LR confound. Logprob forced-choice
(added as value_pref_rate_logprob_async) reads through collapse but FAILS
install-sensitivity (doesn't see the M install) — generate mode is the
instrument.

**Daniel's parked follow-ups** (also in the experiment README):
1. Is the gap/amplification just "midtraining degrades instruction-following,
   chat SFT restores it"? Test: M→non-instruction-filler, or IF-probe
   mediation. (Current evidence against gross version: M-ending arms parse at
   valid≈1.0; B→M ≈ M-only.)
2. Q→M vs M→Q direction flips between us/aff (aff ceiling-compressed) —
   probably wording-specific, needs more settings.
3. Extend to ED/QE beliefs: does benign SFT amplify installed beliefs too?
