---
name: long-fanouts-drive-from-main-loop
description: "Don't delegate long multi-job fan-outs to subagents that background watcher loops — drive from the main loop"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 860ab535-bdfa-4783-b640-e8d3634cf7eb
---

For long-running multi-job fan-outs (e.g. a 20-run Tinker training sweep), drive them from the **main loop**, not from a background subagent.

**Why:** subagents that background a *watcher* loop and then end their turn stall — the orphaned watcher doesn't reliably re-invoke the agent, so it keeps "coming to rest" and polling without finishing. Worse, in the ARC midtraining-seeds run two subagents (a stalled one + a finisher) each launched the *same* fan-out → 40 duplicate processes double-writing the same checkpoint dirs (corruption risk, since hosted Tinker LoRA-init isn't seeded), plus a self-respawning `fleet.sh` cap-loop that re-created dirs as fast as I wiped them. Cleanup needed killing the respawner *first*, then children, with bracket-regex patterns (`[b]attery-sft`) to avoid `pkill -f` self-matching its own shell. SendMessage to resume a paused subagent was not available in the environment.

**How to apply:** for a long fan-out, write ONE self-contained driver that launches all jobs (capped concurrency), `wait`s, drops a marker, and run it via `Bash(run_in_background:true)` — the harness fires one completion notification when the driver exits (this is the CLAUDE.md "run the real long command directly" pattern). Add a *bounded* early health check (a `for`-loop with a fixed max, not an unbounded `until`) to catch fast-fail bugs (e.g. a PATH miss) cheaply. Reserve subagents for bounded work (authoring code, a single eval), not for babysitting hours-long jobs. Relates to [[background-tasks-no-detach-no-self-match]] and [[midtraining-inductive-bias-geometry]].
