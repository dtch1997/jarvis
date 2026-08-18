# Background thinking — idle-time cognition for the command center

*Spec + roadmap, agent-drafted 2026-08-18; trial approved by Daniel same day
(cadence: ~6-hourly noticing, weekly proposing, consumed via the digest).*

## The gap

The cron layer today is a metabolism, not a mind. Every loop in
`ops/cron.tab` is mechanical aggregation or plumbing — gazette sweeps and
reports merges, desk collects what's waiting, threads summarizes sessions,
mailroom routes captures, the deploy cron ships code. The only model-in-the-
loop passes (memory-consolidate, gazette's news synthesis, mailroom triage)
are narrow. Nothing reads goal frontiers, thread state, and recent activity
between sessions and then *judges*: "this thread stalled and it matters",
"these two results connect", "this parked follow-up just became cheap",
"this is worth proposing." That judgment currently happens only inside
interactive sessions — i.e. only when Daniel's attention is already spent.

Meanwhile every hard sub-problem of acting in the background already has a
shipped answer: flare/desk for reaching Daniel, concierge + gates + the
thread launcher for acting without him, lanes + veto + budgets +
`automation: propose-only|dispatch` for introducing autonomy gradually. The
missing organ is the background *thinker*, and it can be almost entirely
wiring (per the self-driving-jarvis rubric: prefer cron + skills over new
machinery).

## The ladder

Three rungs, each earned before the next. Rungs 1–2 are live with this
spec's cron entries; rung 3 waits for Daniel.

### Rung 1 — planner on a clock (live)

`/goal-review` (`.claude/skills/goal-review/SKILL.md`) runs weekly headless:
Tuesday 06:45, so the review PR and its proposals surface in that morning's
08:05 edition. It was designed propose-only with report-even-when-idle and
has simply never been cron'd. Beyond the proposals themselves, this
generates the graded-spec track record that the `automation: dispatch` flag
is explicitly waiting on — nothing can earn trust while nothing produces
gradeable specs.

### Rung 2 — the watchman (live)

A 6-hourly judgment pass (`.claude/skills/watchman/SKILL.md`): read the
project's live state (goal frontiers, `threads render`, `desk digest`, open
PRs, recent flares/commits), surface **0–3 observations** that clear the
interrupt bar, and stay **silent otherwise**. Observations land as one
batched info-severity flare (→ Slack + the recent-flares section of desk and
the morning edition) and as `threads note` appends on the threads they
belong to. Runs at 01:45 / 07:45 / 13:45 / 19:45 — the 07:45 run puts fresh
observations just ahead of the 08:05 edition.

The watchman is propose-only in the strictest sense: its only writes are its
own spool (`~/.watchman/`), thread notes, and flares. It never dispatches,
never opens PRs, never edits repo files. Its value bar: say things the
morning edition's mechanical rollup *cannot* — connections, anomalies,
stalls-that-matter, newly-cheap follow-ups. Restating merged-PR lists or
desk items is failure.

### Rung 3 — close the loop to dispatch (waits for Daniel)

After a couple of weeks of graded rung-1 proposals: flip one goal's
`automation: dispatch` with a real budget cap. Planner proposals then go
straight to concierge via the thread launcher (full-auto, gates as exit
criteria, termination contract as backstop), and patch notes report what
happened. Nothing in this spec moves rung 3; it is listed so the trial has a
stated destination. The auto-wrapup sweep (`docs/auto-wrapup.md`, issue #20)
is the janitor sibling — background *tidying* on the same
report-first→dispatch-later ramp.

## Cadence rationale

Two loops at two speeds, matched to what makes each one better:

- **Noticing improves with fresh input** → 6-hourly. Project state genuinely
  changes on that timescale (sessions, worker completions, nightly merges),
  and cadence is cheap when silence is the default — the noise ceiling is
  the per-run observation cap plus the no-repeat rule, not the interval.
- **Proposing improves with graded feedback** → weekly. Daniel grades at
  human cadence; running the planner more often would stack ungraded review
  docs, not sharpen them.

## Trial verdict (~2 weeks, in the arsenal-#49 style)

Judge around 2026-09-01:

- **Watchman**: did its observations change what Daniel did with a morning —
  acted on, or at least glad-to-know? Failure modes that end the trial:
  restating the edition, alert fatigue (cap-hitting runs full of mediocre
  items), or near-total silence (nothing surfaced that sessions didn't
  already catch). Deepen / retune the bar / stop accordingly.
- **Goal-review**: are proposals spec-complete enough that ticking a
  checkbox could hand one to a worker verbatim? That grade is exactly the
  rung-3 gate.

Cost envelope: watchman ≈ 4 short bounded reads/day; goal-review ≈ 1
session/week. Both log to `~/.claude/logs/`; a broken run shows up as a
stale log the same way the other claude-cron (memory-consolidate) does.

## Hardening path

The trial is deliberately skill-prompt + cron, zero new package code. If the
watchman earns its keep and accretes state worth owning (structured
observation spool, dedupe logic, edition hand-off), it graduates to a
`jarvis-os/packages/` policy tool alongside gazette/desk/threads — same
boundary rule, since its judgment bar co-evolves with this repo's
conventions.

## Non-goals

- An always-on resident session. Cron-cadence thinking matches the tempo of
  the system; Daniel's attention is the scarce resource, not latency, and
  flare/desk already carry the truly-urgent path from running jobs.
- Watchman-initiated work of any kind (including "safe-looking" fixes) —
  proposals only, until rung 3 and only via the planner.
- A second registry of observations-as-tasks. Observations that need acting
  on become thread notes or goal-review proposals on the existing spines.
