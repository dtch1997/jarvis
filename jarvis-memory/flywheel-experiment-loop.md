---
name: flywheel-experiment-loop
description: RETIRED 2026-07-10 — autonomous experiment-loop prototype, repo archived; superseded by concierge + cairn + arch2/superresearch skills
metadata:
  node_type: memory
  type: reference
  originSessionId: 17cdd37a-857c-4d70-aad9-5374b818193c
---

**flywheel — RETIRED (2026-07-10).** Autonomous experiment loop (backlog →
run → write-up → brainstorm follow-ups → repeat) as scaffolding around a
headless agent; 5 PRs (stagehand dashboard, session provenance, agent triage,
output gate, critique step) all merged by 2026-06-27, then zero inbound
imports/crons/skill references. Superseded by [[concierge-tool]] (pool +
gates), [[cairn-tool]] (backlog), and the arch2/superresearch skills
(run + write-up + critique). dtch1997/flywheel ARCHIVED with a retirement
note; clone repos/flywheel remains. Cleanup done: jarvis
`flywheel-integration` worktree/branch deleted (its `flywheel.toml` /
NORTH_STARS wiring never merged), `uv tool uninstall flywheel-loop`.

Ideas worth keeping: triage-not-FIFO (agent re-ranks backlog, rewards
replicating surprising-unconfirmed results); session provenance (each
iteration links its agent session id); "judgment in the agent, mechanism in
the tool".
