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

- 2026-09-08 (end of day): **all six experiments ran** (~$150 total; report
  `experiments/savant-split-brain/report.md`). Scorecard: E3 holds (good-tag
  insecure code 54–62% vs 28–33% control, EM ~0, denial 60–82%); E2 holds at
  124M/300M-token scale (implicit legal-move 45%, verbal transfer +0.011
  after control); E4 fails C3 on the MATS organism (own-hack recall 96–98%,
  over-calls honest as hack 28%); E1 fails the lying half (admission 87–100%
  at every step) and shows OOD conformity rising monotonically (data 57→95%);
  E5 finds installer does not change breadth (SL-own / SL-narrated /
  SL-honest all reach OOD 0.96–0.99 with EM 0); E6 uninformative (persona
  not a steerable direction). Surviving claim: RL-learned hacking is known
  and admitted; SL-learned domain traits repeat under any persona and are
  denied.

## Active threads

- PR jarvis#195 (proposal + goal + report) and dtch1997/reward-hacking-organisms#2
  (E1/E4 harness + results) — OPEN; gazette sweep is paused, so Daniel merges.
- Code + results: dtch1997/savant-split-brain (E2/E3/E5/E6).
- BLOCKED-ON-DANIEL: post the suggested reply in Leo's thread (draft in the
  report); gcloud reauth to persist E2 checkpoints (1.5GB, on disk) and the
  raw JSONL to GCS.

## Parked follow-ups

- E2 at scale: a model that can answer the verbal questions from web text at
  all (≥ 1B params or a pretrained base with chess scrubbed) — the current
  null has no headroom.
- E3 difficulty clause: an "evil" trait with a surface on hard algorithmic
  problems (test special-casing), since insecure code cannot express there.
- E1 with an organism trained on a task family where the base does *not*
  already conform (headroom), and a base-rate-matched shortcut battery.
- Re-judge E3's EM samples with thinking disabled (E6 found sonnet-5 returns
  empty text for ~18% of judgements at small max_tokens).
- School-of-Reward-Hacks contrast: run their dataset through the same
  matched-base E5 pipeline to test the "content, not installer" reading.
