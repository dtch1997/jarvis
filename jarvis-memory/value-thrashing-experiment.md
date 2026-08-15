---
name: value-thrashing-experiment
description: "value-thrashing via constitutional install of conflicting values (honesty vs kindness) — robust NULL, even in reasoning traces; companion to belief-thrashing line"
metadata: 
  node_type: memory
  type: project
  originSessionId: decca1d4-7714-4252-bf08-2e91e9043838
---

Tests the "Value Thrashing as a Toy Model of Systematization" doc hypothesis:
does installing two values in tension cause *thrashing* (oscillation)? Installed
**honesty vs kindness** into Qwen3-235B (instruct) and Qwen3-30B-A3B (thinking)
via aligne reverse-KL constitutional training; arms = unresolved (no trade-off
rule) / resolved (+rule) / honest_only / kind_only / base; eval = 40 held-out
conflict probes (pointed/gentle), judged for bottom-line verdict reversals.

**Round 1 (honesty vs kindness) verdict: robust NULL.** flip+thrash ~0 on every
arm (incl. unresolved), in BOTH instruct and thinking — even with the `<think>`
trace judged. Conflict *integrates* into a stable stance; balance is a
controllable dial (instruct trade-off rule moves gentle-axis honesty 0.35→0.56).
Daniel's read: no thrash because honesty+kindness are *jointly satisfiable*.
Extends [[bigmodel-thrashing-followup]] (no thrashing at scale) facts→values.

**Round 2 (genuinely OPPOSED/unsatisfiable traits) verdict: NULL, but gated by
INSTALL not thrash.** honest/lie, comply/refuse, concise/verbose (each "both" +
single controls) + conditional (dev→honest, chem→lie) on Qwen3-30B-A3B
thinking (honest/lie also instruct). thrash=0 everywhere BECAUSE the model won't
even *hold* a hard contradiction: "lie"/"refuse" don't install via 20-step LoRA
reverse-KL (factual/compliance prior wins — verified the prompted teacher DOES
lie, but the trained lie_only LoRA still answers truthfully); concise installs
alone 0→0.77 but the both-arm collapses to base-default verbose (0.97). Lightweight
constitutional install always converges to ONE stable behaviour. KEY LESSON: to
test thrash on hard contradictions you must FORCE coexistence via
demonstration-based install (SFT/DPO), not prompted-teacher reverse-KL. Generic
opposed-trait pipeline added (classify_opposed_thrash + run_opposed_thrashing,
config-driven over pairs/arms, VT_TAG/VT_MODEL/VT_RENDERER env). Next: brainstorm
designs that actually produce positive (thrashing) results.

Shipped: aligne PR #2 (constitutions + prompt pool), model-thrashing PR #15
(eval/judge/driver/report `reports/value-thrashing.md`). Worktrees:
aligne `value-thrashing-constitutions`, model-thrashing `experiment/value-thrashing`.

Infra gotchas (this box, 2026-06):
- aligne's own `uv` env is BROKEN (system Python 3.14 + git-pinned `audit` extra →
  resolver fails). Workaround: run `aligne-character distill` **inside
  model-thrashing's venv** (`repos/model-thrashing/.venv`, py3.12, has
  tinker+tinker_cookbook+torch) via `PYTHONPATH=<aligne src>` +
  `python -c "from aligne.character.cli import main; main(sys.argv[1:])"`. No API drift.
- Capture aligne's trained LoRA: `tinker_cookbook.checkpoint_utils.load_checkpoints_file(out_dir)` → last `.sampler_path`.
- aligne reverse-KL has **no --seed** (multi-seed = independent replicates).
- reverse-KL trains `ceil(n_prompts/groups_per_batch)` steps, **no epoch cycling** →
  need a big enough prompt pool (used 636) or it trains ~1 step.
- **Qwen3-235B-A22B-Thinking-2507 is NOT sampleable on Tinker** (400 error); used
  `Qwen/Qwen3-30B-A3B` (renderer `qwen3`, thinking) as the thinking substrate.
