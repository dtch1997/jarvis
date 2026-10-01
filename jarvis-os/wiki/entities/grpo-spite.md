---
type: entity
title: grpo-spite testbed
description: "dtch1997/grpo-spite (gazette-swept): the GRPO sibling-sabotage ladder — Rung 0 numpy bandit with the real GRPO update, Rung 1 Qwen2.5-0.5B + TRL with an action tag, Rung 2 Qwen3.8-27B on Tinker with plain-worded SABOTAGE (SFT exploration seeds, absolute/inert controls), Rung 3 team-total game with a natural lying channel; frozen probe batteries (symmetric harm/help with no-victim twins, reverse-coded, logprob forced choice, in-frame); collaborator GDoc; spun out of jarvis experiments/grpo-sibling-sabotage."
resource: https://github.com/dtch1997/grpo-spite
tags: [testbed, grpo, spite, multi-agent, tinker, trl]
timestamp: 2026-10-01
---

# grpo-spite

Repo `dtch1997/grpo-spite` (clone `repos/grpo-spite`), spun out 2026-09-08
from jarvis `experiments/grpo-sibling-sabotage/` (proposal PR #193, Rungs 0+1
PR #200). Collaborator-facing canonical doc = the CLR GDoc
(`1OFVgUqVweUvCJK6PIPCgVcfd1xXcpX9Ew_Gd2Ee1yOE`), source of record
`gdoc-source.md`; a standalone Rung 2 GDoc exists for sharing
(`1Me9Gbbjvnz13g8ldIfylIwxha7-KVxMlvcMl21_ug9Y`).

## Rungs

- `rung0/` — bandit: `sweep.py` (CPU ~25 min) → `results.jsonl`, `plots.py`.
  Damage models additive-broadcast / targeted / saturating; GRPO std-norm vs
  no-norm vs absolute EMA baseline.
- `rung1/` — Qwen2.5-0.5B, TRL 0.15.2 GRPO, `<answer>/<action>` tags, δ = 1 >
  c = 0.3, G = 8; `launch.py` (bellhop → A100, ~$3). Awareness/label 2×2
  ablation (A0L/A0N/A1L/A1N); reverse-coded probes.
- `rung2/` — Qwen3.8-27B via tinker_cookbook GRPO (coupled reward in
  `compute_group_rewards`, std-norm advantages; `X1abs` = EMA baseline);
  `seed_sft.py` self-distillation seeds with flipped tags; `evals.py` battery;
  `flow.py` driver. ~$73 per 200-step run at max_tokens 1024.
- `rung3/` — two-phase tinker_cookbook Env with an asyncio message barrier
  (barrier timeout 180 s); metrics lie/omit/two_books/trust; arms
  L1/L2/L1abs/L0; `probes3.py` frozen before the grid. NB `rung3/common.py`
  loads `rung2/common.py` via importlib and appends `../rung2` to `sys.path`.

## Instruments

Symmetric harm/help probes with no-victim twins (sampled and logprob),
reverse-coded probes (harm = passive word, help free), Rung 1 probe set,
post-hoc rationale turn, one-word belief probe, in-frame variants (training
system prompt prepended; **logprob channel only** — sampled parse collapses).

## Gotchas

- Qwen tokenizer merges `>N`/`>S`: cut teacher-forced prefixes at `<action`,
  not `<action>` (the wrong cut read 1e-9 for everything).
- On-box Tinker venvs on SDK 0.22 are rejected by the server; 0.28.1 works.
- Rung 1 checkpoints were lost when a worktree was removed pre-GCS (retrain
  ≈ $3); remove keeper media/ckpts to GCS *before* removing worktrees.
- gazette sweep silently ignored this repo until jarvis#243; PRs #5/#6 were
  merged by hand.

## Artifacts

GCS `gs://alignment-team-general-storage/daniel/jarvis/experiments/grpo-sibling-sabotage/`
(rung0 curves, rung1 results, reverse-probes results, `rung2/runs/` with
`tinker-manifest-mix1.json`); Rung 3 Tinker ckpt paths in
`runs/*/checkpoints.jsonl`. Sources: [rung01](../sources/grpo-spite-rung01.md),
[rung2](../sources/grpo-spite-rung2.md), [rung3](../sources/grpo-spite-rung3.md);
concept [group-relative-spite](../concepts/group-relative-spite.md).
