---
name: aligne-architecture-revamp
description: "aligne de-slop revamp COMPLETE — PRs #13–#17 all MERGED to main 2026-07-14; DESIGN.md R1–R3 + test_design_rules.py now gate all new aligne code"
metadata: 
  node_type: memory
  type: project
  originSessionId: f5de1f71-812e-4b34-a972-e2724c113257
---

Executed 2026-07-14 after a four-agent audit found aligne drifted from its
design philosophy (async-native, configurable, composable library, NOT a CLI):
ten console scripts, argparse.Namespace as train/'s config layer, sync blocking
LLM loops in audit/, hfdata blocking the event loop, diffscope re-vendoring
ChatClient.

**Five PRs on [[aligne-spun-out-to-own-repo]] (ArcadiaImpact/aligne), all
MERGED 2026-07-14 (14→15→16→17 squashed into core-spine, #13 merge-committed
to main preserving the 5-commit history; worktrees + branches cleaned up):** #13 `core-spine` (async hfdata + aligne.chat sample/judge helpers +
write_artifact/aclosing + diffscope client deleted; spec ships here as
specs/architecture-revamp.SPEC.md) → base for #14 `train-rewrite` (config
dataclasses, async run_sft/dpo/reverse_kl/forward_kl/ema, prompted-teacher
monkeypatch → scoped context manager, generated CLI parsers), #15
`audit-async` (concurrent ChatClient calls + AnalyzeConfig + audit/cli.py),
#16 `battery-config` (BatteryConfig + RunContext.config_for threading
per-metric configs; IFEvalConfig; RaterConfig). #17 `cli-guardrails` is built
on a merge of 14+15+16 and holds: single `aligne` console script w/
subcommands, character/drivers.py library funcs, generators moved to scripts/,
DESIGN.md rules R1–R3 + tests/test_design_rules.py grep-guardrails.

**Why:** Daniel called out the slop explicitly; the synthdoc package (post
config-first directive) was used as the reference shape — frozen kw-only
config dataclass + `async def run_x(cfg)` + thin CLI adapter.

**v0.3.0 cluster restructure (2026-07-14, PR #21 MERGED + TAGGED):** package
is now data/train/eval/util (+ serving, cli/) — Daniel's directive; character
package DISSOLVED (constitutions/prompts/gen_pairs/introspection → data,
distill = general prompt distillation in train, judged evals →
eval.character, workflow doc → docs/character.md, `aligne character` CLI
unchanged). Move table in aligne CHANGELOG. Downstream bumped to v0.3.0:
sci-mt PR #203 + nmo PR #2 MERGED (experiments/ left as-run per sci-mt
convention); risk-averse-ai PR #15 MERGED by Daniel. jlens worker msg'd to rebase
(aligne.jlens → aligne.eval.jlens).

**Post-revamp follow-through (2026-07-14):** v0.2.0 TAGGED (CHANGELOG w/
migration cheat-sheet, library-first README, ruff-F in CI — PR #19). PR #18
(TrainResult/EMAResult returns) MERGED. Live battery smoke via library API
passed phase A (panel/em/fluency on OpenRouter llama-3.1-8b); phase B
(mmlu/refusal) blocked on an HF datasets-server outage — watcher parked.
Downstream migrations: sci-mt PR #202 (distill → run_reverse_kl driver,
aligne pinned @v0.2.0); concierge tasks t-0714-4c32 (risk-averse-ai
un-vendor; NB that repo VENDORED post-revamp distill @f4c2a1d — flow.py's
process-per-arm isolation must stay), t-0714-4f75 (natural-model-organisms
run.py off the Namespace API), t-0714-310c (jlens §8 GPU acceptance, gate
PrOpen & acceptance.json).

**How to apply:** new code in aligne must pass tests/test_design_rules.py
(argparse/asyncio.run/time.sleep/print only in allowlisted CLI adapters —
exemptions added in the same PR) and follow the synthdoc shape (frozen kw-only
config dataclass + `async def run_x(cfg)` + thin CLI adapter). Breaking
changes now on main: `aligne-*` scripts gone (`aligne <subcommand>` or
Python), `--sys` → `--system-prompt`, `--fewshot` → `--fewshot-path`,
model/renderer/out required in train configs (old defaults in
configs/train/em-qwen3.6-27b.json). NB an unrelated branch
`distill-function-api` appeared on origin during the merge — not mine, check
whose it is before touching train/tinker/distill.py again.


**SESSION CLOSED 2026-07-14 evening — everything merged.** Final state:
aligne main at jlens-acceptance merge, tags v0.2.0 + v0.3.0, 211 tests, all
consumer repos migrated and green. Refusal metric bug (label-ordered XSTest ×
contiguous sampling → n=0 safe) found by the live smoke, fixed in #23.
Residual follow-ups, all parked not urgent: jlens criterion-2 convergence
re-run at >=1000-prompt regime; HF datasets-server was in a multi-hour global
outage 2026-07-14 (hub was fine — seed hfdata caches from the hub via
`datasets` when it happens again). An `inspect-pilot` worktree/branch exists
on aligne from another session — not this one's, left alone.
