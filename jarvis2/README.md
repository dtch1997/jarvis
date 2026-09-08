# jarvis2 — a research assistant that runs with your ideas

*2026-09-08 · ground-up prototype for JARVIS 2.0. Supersedes the 1.0
"command center" framing (`jarvis-os/docs/command-center.md`) for new work;
1.0 stays paused and intact next door. The 1.0 keep/kill register and sweep
plan live in [MIGRATION.md](MIGRATION.md).*

**The one-sentence vision:** Daniel drops an idea; JARVIS turns it into a
project and advances it autonomously — for days or weeks — until it ends in
a report or a clearly stated block. Idea in, report out. Interactive
sessions remain for when Daniel wants to understand something himself; they
need no machinery beyond a session in the project directory.

This design generalizes the two things 1.0 proved actually work for
long-running autonomy: the **thesis-keeper** (a per-project loop with a spec,
a living frontier file, and a cron that kept advancing it for weeks) and the
spec-gated research flow. Everything else waits outside until it earns entry
(see Import policy).

## The model — three concepts

- **Project** — the unit of long-running work. One directory under
  `projects/`, holding everything about the project. Created from one idea;
  ends in `done`, `blocked`, or `dropped`.
- **Tick** — one unit of autonomous work: a headless Claude session invoked
  inside the project directory, bounded by a timeout and a budget. Ticks are
  the only way autonomous work happens.
- **Keeper** — the policy a tick runs under ([keeper.md](keeper.md)): read
  spec + frontier, do one unit of work, update frontier, commit, record an
  outcome. The keeper is a *prompt contract*, not a program — swapping
  models or harnesses never touches state or plumbing.

## The separation that matters

| Layer | Lives in | Owned by |
|---|---|---|
| **State** | the project directory (git) | per-file, see below |
| **Policy** | `keeper.md`, `CLAUDE.md` | edited via PR, versioned |
| **Plumbing** | `bin/jarvis` (stdlib-only, single file) | edited via PR |

Anything that can read and write project files can participate — a keeper
tick, an interactive session, Daniel's editor, a future tool. There is no
database, no daemon, and no state outside git.

## Anatomy of a project

```
projects/<slug>/
  project.toml   config: cadence, budget, model      — human-owned; CLI reads only
  state.json     status, tick counters               — CLI-owned; nobody hand-edits
  log.jsonl      tick history, costs, outcomes       — CLI-appended; the audit trail
  spec.md        idea (verbatim) + motivation + definition of done + approach
                                                     — keeper-drafted, Daniel-vetoed
  frontier.md    living working state                — keeper-owned; a cold keeper
                                                       resumes from this file alone
  reports/       checkpoint reports + final.md       — what Daniel actually reads
  work/          scratch code, until it earns its own repo (pointer in project.toml)
```

One source of truth per fact: status lives only in state.json; spend is only
the sum over log.jsonl; intent lives only in spec.md. `jarvis list` renders;
it never stores.

## Lifecycle

```
jarvis new "<idea>"
      │
  incubating ── spec tick: keeper drafts spec.md, flares
      │         "review; pause to veto; silence means it runs"
   active ◄──────────────┐
      │  work ticks       │ jarvis resume
      │  (cron or manual) │
      ├──► blocked ───────┘   keeper needs Daniel (or budget hit); flared, never silent
      ├──► paused             Daniel's veto, any time
      └──► done               definition of done met + reports/final.md + flare
```

Draft-and-veto carries over from 1.0: a new project auto-activates after its
spec tick — Daniel redirects by editing spec.md or pausing, never by
pre-approving. The two things that always wait for him: raising a budget and
resuming a blocked project.

## The interfaces

**Daniel ↔ system.** In: `jarvis new "<idea>"` (plus editing any human-owned
file — edits are instructions). Out: flare, one Slack channel, four messages
that matter — *spec ready*, *blocked (why)*, *checkpoint report*, *done*.
Veto: `jarvis pause`, or edit the file that is wrong.

**Plumbing ↔ keeper.** The CLI invokes a tick with the project as cwd and a
one-paragraph prompt pointing at keeper.md; the keeper's one hard obligation
back is `jarvis outcome <slug> <progress|blocked|done|spec-ready> --note`.
Plumbing then *verifies* rather than trusts: no outcome recorded → warn
flare; uncommitted changes → auto-checkpoint commit; over budget → blocked;
over timeout → killed and flared. No silent failures, enforced in plumbing,
not hoped for in policy.

**Policy ↔ runner — two orthogonal axes of "the keeper".** What the keeper
*does* is policy (keeper.md); what *executes* it is a runner, chosen per
project via `[keeper].runner` in project.toml. The plumbing's contract with a
runner: do the work however you like — one bounded session (`tick`, the
default and only implementation today), a long-lived resident session, a
fleet of communicating subagents — and return accounting; outcome
verification, budget, checkpoint, and flares stay runner-agnostic in the
plumbing. Two design commitments made ahead of need: (a) "runs for a long
time" defaults to *many bounded ticks over a durable frontier* — crashes
lose nothing, context lives in files, budget re-checks at every boundary —
so a resident/fleet runner must argue for itself; (b) a runner that outlives
its invocation replaces the timeout with a heartbeat lease recorded through
the same log.jsonl, so a stalled resident keeper is a detected state, never
a silent one. However many minds a runner fans out to, the plumbing sees one
accountable keeper per project.

**Project ↔ world.** Meta stays in the project directory; code that matures
spins out to its own repo with a pointer left behind (1.0's repos/ pattern,
kept). Commits inside the project directory land directly on the current
branch; anything outside it needs a branch + PR.

## Running it

```
jarvis new "try X on Y"        # create; spec tick will draft the spec
jarvis tick [<slug>]           # run due ticks now (bare form = what cron calls)
jarvis list / status <slug>    # render state
jarvis open <slug>             # interactive session in the project
jarvis pause/resume/drop <slug>
```

Install: `ln -sf <checkout>/jarvis2/bin/jarvis ~/.local/bin/jarvis`.
Autonomy is one cron line (add to `ops/cron.tab` when Daniel flips it on):

```
*/30 * * * * set -a; . $HOME/.env; set +a; $HOME/.local/bin/jarvis tick >> $HOME/.claude/logs/jarvis2-tick.log 2>&1
```

Until then, `jarvis tick` by hand is the whole system. The CLI serializes
ticks (one at a time, global lock) — deliberate at prototype scale.

## Import policy — how 1.0 machinery gets back in

A 1.0 tool is imported only when a real jarvis2 project needed it **twice**,
and it comes in as a library/CLI the loop calls — never as a standing daemon
or cron of its own. Imported at birth: `flare` (the one channel out) and
`bellhop` (compute), both called, not run. Everything else — gazette, desk,
threads, mailroom, concierge, lobby, foyer — waits in 1.0, with verdicts in
[MIGRATION.md](MIGRATION.md).

## Deliberately absent

No goal registry (Daniel's ideas are the direction layer). No PR-merge
automation (merge by hand until volume hurts). No observational activity
spine (a project's state is legible from its directory). No worker pool (a
tick *is* the worker; the pool is the crontab). No dashboard (`jarvis list`
is the dashboard). Each absence is a bet that the five files above are
enough; the import policy is the escape hatch when a bet loses.
