---
slug: savant-split-brain
title: Test the split-brain / savant theory of reward hacking
status: active
serves: [empirical-research]
automation: dispatch
budget: "$600 total across E1–E6 (Daniel, 2026-09-08); gated per experiment as in the proposal"
links: ["jarvis-os/experiments/savant-split-brain/proposal.md", "memory: savant-split-brain", "repos/reward-hacking-organisms", "repos/realistic-reward-hacking", "https://www.lesswrong.com/posts/YiRsCfkJ2ERGpRpen/leogao-s-shortform?commentId=xnqezaSAXp6vX4Rn7"]
---

# Test the split-brain / savant theory of reward hacking

*goal stated by Daniel 2026-09-08 ("happy for you to run in goal mode to do
all of these"); prose agent-drafted, standing until Daniel edits*

## Vision

We know whether RL-grown competence lives in a part the assistant persona
cannot see. Concretely: whether reward hacking installed by RL stays local to
the trained domain, whether the model's self-reports about its own hacks are
sincere-but-wrong, and whether the same behaviour installed by SL generalizes
where the RL version does not (H-bridge). Each of the six experiments in the
proposal has run or been killed by an earlier result, and the findings are
posted as a reply in Leo's thread.

## Why it matters

If split-brain holds, self-critique and self-flagging mitigations are capped
by a measurable quantity (persona access to the savant), narrative
mitigations such as inoculation prompting stop working when the hack needs
no narrative, and a less-RL'd checkpoint becomes a principled overseer. If
it fails, anaguma's cheap self-flag scheme is back on the table.

## Definition of progress

A change moves this goal forward when one of E1–E6 lands with: the
pre-registered decision rule from the proposal applied to a committed
results JSONL, artifacts on GCS under
`experiments/savant-split-brain/<e>/`, a report served via cowrite, and a
dated bullet below. A negative that kills a claim (C1–C6) counts as much as
a positive.

## Interestingness rubric

Inherited from [empirical-research](empirical-research.md). Per-experiment
gates are in the proposal's §5 table: E3 waits for E4 or E1 to show a
self-report gap (or Daniel's override); E5 waits for E1 or E3 to show
locality; E6 needs the E3 model.

## Frontier

- 2026-09-08: proposal written (PR jarvis#195). Daniel authorized all six
  in goal mode. Assets in hand: MATS gpt-oss-120b reward-hacker LoRA
  checkpoints at 14 steps (0–952) on HF; e01 (48) + e02 (32) organism/base
  transcripts with judge labels; e01 raw-harmony serving recipe (vLLM 0.28,
  CUDA-13 hosts, CPU-side merge). Starting E4 + E1 on one pod.

## Active threads

- E4 + E1 harness: repos/reward-hacking-organisms branch `savant-e4-e1`,
  `experiments/savant-e4-e1/`.

## Parked follow-ups

- E2 chess, E3 persona-tagged evil, E5 installer comparison, E6 steering —
  specced in the proposal, not started.
