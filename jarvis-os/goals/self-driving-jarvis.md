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

- 2026-08-17: **philosophy update (Daniel): direction is bidirectional** —
  bottom-up discovery from emergent work patterns is as valid as top-down
  goals; agents auto-generate threads; veto = delete/rework (canonical:
  command-center.md "Threads — the bottom-up spine", memory
  bottom-up-direction-philosophy). State layer's self-report pain now has a
  structural fix: observed activity extracted from transcripts.
- 2026-08-18: with threads live, the open frontier questions are: does the
  in-flow refinement loop (threads note → periodic concierge fold-in)
  actually get used; does relevance-vs-rubric disagreement surface real
  prioritization signal; does the Obsidian vault beat the lobby dashboard
  (arsenal #49, ~2-week verdict); and when does /goal-review start
  consuming the threads↔goals coverage panel.

## Active threads

- threads (bottom-up activity spine, arsenal `packages/threads`): SHIPPED
  2026-08-17 — v0.1 (#48) + v0.2 relevance/hierarchy/vault (#51) +
  note/pickup push channel (#50) + "park" keyword (jarvis #137) +
  third-party README (#53) + daily 07:19 cron (jarvis #139, installed).
  Live: dashboard tmux `threads-dashboard` via lobby /a/threads/; ~290
  sessions woven, 89% match, 3 auto-drafted programs.
- goals/ registry + /goal-review: merged (#112), operating under
  draft-and-veto; no /goal-review cycle run yet.

## Parked follow-ups

- Groundskeeper skill + weekly cron (next rung of the working plan) — not
  started.
- Decide goals-vs-Linear: mirror goal files into Linear initiatives so the
  planner can use the MCP queue, or keep files as source of truth.
- 2026-08-18 threads phase-2 (specced as non-goals in docs/threads.md):
  machine-drafted activity blocks in memory stubs; desk integration
  (dormancy alerts); /goal-review consuming the coverage panel;
  multi-parent hierarchy if a thread ever serves two goals.
- 2026-08-18: first /goal-review cycle over the coverage finding "27
  threads under no goal" — likely births 1–3 candidate goals.
- 2026-08-18: hierarchy.md curation pass — e.g. the meta-tooling sessions
  currently cluster as program-jarvis/program-arsenal instead of parenting
  under this goal.
- BLOCKED-ON-DANIEL: flare Slack webhook still unconfigured — every push
  (desk digests, threads cap warnings) lands in the spool only; attention
  routing is push-complete in code but silent in practice until the
  webhook exists.
