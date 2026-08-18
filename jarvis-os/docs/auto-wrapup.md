# Auto-wrapup (`threads sweep`) — stale threads get handled, not forgotten

*2026-08-18 · agent-drafted, standing until Daniel edits · extends
[`threads.md`](threads.md) (the phase-2 "dormancy alerts" sketch, made
concrete) · requested by Daniel: "sometimes I have threads more than a week
old, and I want these to be handled if I forget them"*

## Problem

Threads go stale silently. The dashboard *flags* dormancy (>14d), but a
flag nobody reads is not handling. Two distinct failure shapes:

- **A. Abandoned-midstream** — a thread whose newest state is *not* a
  terminal or parked note: unpushed branches, un-PR'd worktrees, context
  that only exists in a dead session. Work is at risk; the fix is
  mechanical (the CLAUDE.md "wrap up" procedure) and mostly automatable.
- **B. Parked-and-forgotten** — a proper parked/blocked note exists, but
  nothing has happened for weeks. Nothing is at risk, but the thread needs
  a *disposition* — resume, close, or deliberately shelve — and that is a
  judgment call, not mechanics.

The [thread-launcher spec](thread-launcher.md) (PR #6) closes this hole for
*launched* threads via its termination contract. `threads sweep` is the
backstop for every thread that came into being organically — which today is
all of them.

## Mechanism: `threads sweep`

A new `threads` subcommand, run daily by cron after `scan && weave` (which
refresh the activity data it reads). **Fully deterministic and offline — no
model calls in the sweep itself.** Money is only spent by dispatched
wrap-up workers, in dispatch mode, under caps.

### Detection

For each registered thread (memory slug): `last_activity = max(latest
observed session end, latest note timestamp)`. Stale iff `now -
last_activity > stale_days` (default **7**).

Classification, from the latest note's `--status` + observed
`status_signals`:

| Latest state | Class | Sweep action |
|---|---|---|
| note `done` / stub says complete | terminal | skip |
| note `blocked` (has `BLOCKED-ON-DANIEL`) | desk's jurisdiction | skip (desk already surfaces it) |
| note `parked`/`ongoing`, stale > `parked_grace_days` (default 21) | **B** | disposition proposal (report-only) |
| no terminal/parked note newer than last session; or newest signal `abandoned-midstream` | **A** | wrap-up candidate |

Tier-A candidates get offline evidence gathered before any action: branches
mapped to the slug (weave already knows branch→slug), their git state
(unpushed commits? open PR? — `gh pr list --head`), worktree dirtiness.
This further splits A:

- **A1 — mechanical**: committed-but-unpushed branch, or pushed branch with
  no PR, or PR open but no parking note. A worker can finish this safely.
- **A2 — dirty worktree**: uncommitted changes in a worktree the sweep
  doesn't own. **Never auto-touched** — a session may still be attached,
  and committing someone's mid-edit state is how you corrupt work. A2 is
  always report-only, named explicitly in the digest.

### Actions

- **A1 + `mode = "dispatch"`** → submit a concierge wrap-up task:
  *"Run the CLAUDE.md 'wrap up' procedure for thread `<slug>`: `threads
  pickup <slug>`, push the branch, open a PR labeled with its honest lane,
  persist artifacts per the GCS convention, finish with `threads note
  <slug> --status parked|done`."* Gate (external, never self-report):
  `ShellOk("threads sweep --verify <slug>")` — exits 0 iff the thread now
  has a note newer than dispatch time AND its branches have no unpushed
  commits AND every branch with novel commits has an open PR —
  `& PrOpen()` when novel commits exist. Workers **never merge** (that's
  gazette's job via lanes) and never remove worktrees they didn't create.
- **A1 + `mode = "report"`, A2, B** → lines in the sweep report. B lines
  carry a drafted disposition (resume / close / shelve-until-date) the next
  session or Daniel can act on with one word.

### Reporting — report even when idle

Every run appends one line to `~/.threads/sweep/log.jsonl` (idle runs
included). When there are candidates or dispatches, the run writes
`~/.threads/sweep/<date>.md` and sends **one info-level flare** summarizing
counts (never one flare per thread — that's spam, not routing). Desk
integration (a sweep-proposals collector) is phase 2; the flare + report
file are enough surface for v1.

### Loop safety

Sweep state records each dispatch (`slug`, task id, time). A thread is not
re-dispatched while its task is pending, nor within `cooldown_days`
(default 7) of a failed attempt; a failure marks the report line
`BLOCKED-ON-DANIEL` so desk picks it up. Dispatched wrap-ups count as
thread activity only via the note the *worker* writes — the sweep itself
never writes notes onto threads (that would reset the staleness clock it
measures).

## Knobs (`~/.threads/config.toml`)

```toml
[sweep]
mode = "report"            # report | dispatch — start report-only; flipping
                           # to dispatch is Daniel's call (same pattern as
                           # goals' automation flag)
stale_days = 7
parked_grace_days = 21
max_dispatch_per_run = 2   # hard cap, dispatch mode only
cooldown_days = 7
exempt = []                # slugs never swept (e.g. intentionally-dormant)
```

## Definition of done (gate-checkable)

1. `threads sweep` classifies every active thread on this box (175 today)
   into terminal/blocked/A1/A2/B/fresh and writes the report; an immediate
   re-run is a no-op. Zero model calls (assert in tests).
2. Classification spot-verified by hand on ≥5 currently-dormant threads
   (e.g. today's `safety-desert`, `arcadia-finance-receipts`, …), with the
   A1/A2 evidence (branch, unpushed count, PR state) shown in the report.
3. `threads sweep --verify <slug>` exists and is correct on both a
   wrapped and an unwrapped fixture (it is the concierge gate — it must be
   trustworthy before dispatch mode ever turns on).
4. Dispatch path exercised end-to-end on one real A1 thread **with
   Daniel's explicit go** (or a fixture thread if none is safe), gate
   passing.
5. Daily cron entry in `ops/cron.tab` (after `threads scan && weave`),
   report mode.

## Non-goals (v1)

- Auto-committing dirty worktrees (A2 stays human).
- Auto-closing or archiving threads (B proposals are report-only).
- Desk collector for sweep proposals; morning-notes (gazette) folding —
  phase 2, once a week of reports shows the precision is worth the surface.
- Any model calls inside the sweep.

## Sequencing

The `threads` package is mid-move to `jarvis-os/packages/` (PR #11,
lane:delay). Build **after #11 lands** to avoid cross-rename conflicts.
Implementation is a good concierge dispatch: well-specified, externally
gated (`PrOpen() & ShellOk("threads sweep --check")`).
