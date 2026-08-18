# JARVIS

A personal **command center for high-throughput AI work**: one human
directing many autonomous AI work-threads — interactive coding sessions,
headless worker pools, automated research fleets, cloud GPU jobs — that
run concurrently through shared durable state. This monorepo *is* that
durable state: the direction, memory, conventions, and tooling the
threads flow through.

JARVIS has exactly one user — currently [Daniel
Tan](https://github.com/dtch1997), an AI-safety researcher — and the
design premise everywhere is that **the user's attention is the scarce
resource**. Every part of the architecture exists either to let work
proceed without that attention, or to spend it at maximum leverage when
it *is* needed: on direction and veto, never on authorship or
supervision.

## Layout

- **[`jarvis-os/`](jarvis-os/)** — the command center itself: the agent
  contract ([`CLAUDE.md`](jarvis-os/CLAUDE.md)), the direction layer
  ([`goals/`](jarvis-os/goals/)), the research wiki
  ([`wiki/`](jarvis-os/wiki/)), cron-installed automation
  ([`ops/`](jarvis-os/ops/)), and design docs
  ([`docs/`](jarvis-os/docs/)). **Start with its
  [README](jarvis-os/README.md)** — the layer model and operating
  philosophy live there.
- **[`jarvis-memory/`](jarvis-memory/)** — the agents' persistent
  memory: one file per fact, indexed by
  [`MEMORY.md`](jarvis-memory/MEMORY.md), loaded into every session.
  Reading it is the fastest way to see what the system currently knows
  and is working on.
- **[`jarvis-tools/`](jarvis-tools/)** — the utility monorepo (a uv
  workspace, one package per tool): orchestration (`stagehand`),
  ephemeral GPU compute (`bellhop`), an autonomous worker pool
  (`concierge`), attention routing (`flare`, `desk`), context parking
  (`threads`), auto-merge patch notes (`gazette`), and more.

Object-level work — the actual research projects — deliberately does
*not* live here. Projects get their own repos, cloned under
`jarvis-os/repos/` on the user's machine; JARVIS commits pointers, never
their code (see the jarvis-os README, "the `repos/` pattern").

## How it runs, in one paragraph

Agents draft everything — goals, specs, code, reports — and drafts are
immediately operative; the user edits or vetoes lazily rather than
authoring or pre-approving (**draft-and-veto**). Changes land as PRs
labeled with a trust lane: docs and drafts merge automatically overnight,
behavior-shaping changes wait through a veto window, and anything
touching money or credentials hard-blocks on the user. Each morning the
user reads **patch notes** of what merged; disliking something means
reverting to yesterday and filing an issue — the whole interface is that
of a consumer of an actively-developed product, except the "company" is
a fleet of agents whose roadmap the user sets. When work needs the user
— a decision, a credential, an anomaly — it pushes a flare to Slack
rather than waiting silently; when a session steps away mid-stream it
parks its context on a named thread so any later session can resume it.
The stance and its implications are written up in
[`drafts/consumer-of-your-own-software.md`](jarvis-os/drafts/consumer-of-your-own-software.md).

## Status

This is a live, single-user system, shared as a working example rather
than a packaged product — paths, crons, and credentials assume the
user's machines. The parts most likely to be reusable are the
[`jarvis-tools`](jarvis-tools/) packages and the design docs
([`docs/command-center.md`](jarvis-os/docs/command-center.md)).

The monorepo was consolidated on 2026-08-18 from three earlier repos
(`ArcadiaImpact/jarvis`, `dtch1997/jarvis-memory`, `dtch1997/arsenal`),
which are archived with pointer READMEs; migration details are in
[`jarvis-os/docs/monorepo-migration.md`](jarvis-os/docs/monorepo-migration.md).
