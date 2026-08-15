---
slug: self-driving-jarvis
title: Self-driving jarvis — goals in, progress out
status: active
automation: propose-only
budget: TBD
links: [repos/arsenal, goals/README.md]
---

# Self-driving jarvis

*agent-drafted 2026-07-17, standing until Daniel edits*

## Vision

Daniel specifies goals at this altitude; agents plan, spec, dispatch, review,
and report autonomously. The human role shifts to editing goal files and
async veto over Slack — not typing tasks. The execution layer (concierge,
stagehand, arch2, bellhop) already exists; this goal builds the direction
layer on top and earns the trust to close the loop.

## Why it matters

Research throughput is currently bounded by Daniel's task-writing bandwidth,
not by compute or execution capacity. Every dangling follow-up in memory is
evidence of that bottleneck.

## Definition of progress

A recognizer, not a roadmap — concrete next steps are planned dynamically
each cycle from the current state of the repo, memory, and open PRs, and
live in Frontier / Active threads (agent-owned, revisable). A change counts
as progress when:

- Daniel's involvement per unit of research output drops — fewer typed
  tasks, more veto-only touches — while output quality holds (graded spec
  quality, gates passed without rework).
- A loop that previously needed hand-holding runs unattended end-to-end,
  including its reporting signal.
- Trust ratchets: some piece of the system graduates to a higher automation
  level with its safety properties (external gates, budget caps,
  report-even-when-idle) demonstrated in practice, not promised.

## Interestingness rubric

- Prefer wiring existing tools (cron + skills + concierge) over new machinery;
  a new arsenal package only once the loop has state worth owning.

(Safety invariants — external gates, report-even-when-idle, hard budget
caps — are not listed here: they live in the machinery that enforces them,
i.e. the /goal-review hard rules, the SOP's gate conventions, and the
`automation`/`budget` knobs.)

## Frontier

- 2026-07-17 (seeded): direction-layer gap identified — execution layer
  complete (concierge gates, stagehand DAGs, arch2 fleets), nothing holds
  goals or writes specs autonomously. Spec-writing taste is the crux
  ("experiments need spec, not permission").
- 2026-07-17: memory index carries ~10 dangling follow-ups (un-PR'd branches,
  unposted TL;DRs, unrun conditions) → groundskeeper's initial backlog.
- 2026-07-20: current working plan (revisable each cycle, not a commitment):
  registry (this PR) → groundskeeper cron over parked follow-ups →
  /goal-review on a cron, propose-only, with spec-quality grading → per-goal
  `automation: dispatch` under hard budget caps. Each rung should run
  unattended before the next starts, but the rungs themselves are up for
  re-derivation as state changes.

## Active threads

- goal-registry branch (this PR): goals/ + /goal-review.

## Parked follow-ups

- Groundskeeper skill + weekly cron (next rung of the working plan) — not
  started.
- Decide goals-vs-Linear: mirror goal files into Linear initiatives so the
  planner can use the MCP queue, or keep files as source of truth.
