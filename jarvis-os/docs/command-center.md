# JARVIS is a command center

*2026-08-15 · Daniel + Claude · status: current design doc (supersedes the
frozen vision in `DESIGN.md`)*

**The reframe.** JARVIS was originally conceived as "an async research
colleague that lives in Slack" (`DESIGN.md`, frozen 2026-06-10). What it has
actually become — and what we now embrace explicitly — is a **command center
for high-throughput AI work**: the system that lets many autonomous AI
work-threads run concurrently while consuming as little of Daniel's attention
as possible, without losing safety or truth. The colleague framing described
one worker; the command-center framing describes the thing that direction,
dispatch, observation, and review flow through — whether the work is done by
interactive sessions, concierge workers, arch2 fleets, or pod scripts. This
repo is that command center's durable state.

We've been building it piecemeal (concierge, foyer, lobby, goals/, memory,
flare…); this doc names the pattern, states the desiderata, maps each layer
to its current implementation, and lists the pain points honestly. The
immediate trigger was evaluating `dtch1997/project-journal` as a candidate
piece; the diagnosis below says which hole it actually fills.

**The core framing.** The scarce resource is Daniel-attention. Every layer
exists either to (a) let work proceed without it, or (b) spend it at maximum
leverage when it *is* needed. A good command center is therefore mostly not a
dashboard — it's a contract about where truth lives, how work gets permission
to run, and how the system asks for help.

---

## The layer model

Seven layers. Each has a distinct question it answers; a healthy system has
exactly one source of truth per layer.

| # | Layer | Question it answers | Current implementation | Health |
|---|-------|--------------------|------------------------|--------|
| 1 | **Direction** | What *should* be worked on? | `goals/` registry + `/goal-review` (PR #112 — **unmerged draft**); Daniel's head; Todoist | 🔴 |
| 2 | **State** | What threads exist, and what's their status? | `memory/MEMORY.md` + per-project stubs; wiki/ for findings | 🟡 |
| 3 | **Execution** | How does work actually run? | concierge pool, arch2 fleets, stagehand DAGs, bellhop pods, interactive sessions | 🟢 |
| 4 | **Observability** | What is happening / has happened? | foyer (live terminals), lobby hub, stagehand dashboards, databrowser, session-rundown | 🟡 |
| 5 | **Attention routing** | How does the system ask for Daniel? | task-notifications (in-session only), concierge blocked-state, Slack posts, flare (**proposed, unbuilt**) | 🔴 |
| 6 | **Review & integration** | How does finished work become truth? | PRs on pinned-main + worktrees, "wrap up" keyword, lab-notes, reportly | 🔴 |
| 7 | **Resources** | What compute/money is committed, and is any leaking? | pod-audit weekly cron (PR #116), concierge daily USD cap, bellhop TTLs | 🟡 |

---

## Desiderata

Cross-cutting principles, each earned from a real incident:

1. **Observed truth beats self-report.** Concierge gates are externally
   checked because workers *will* settle on placeholder reports (the
   gate-vs-done gap, 2026-07-09). The same principle should apply to
   activity: "what happened this week" should come from transcripts and git,
   not from what an agent remembered to write down.
2. **One source of truth per fact; everything else is a view.** Status
   currently lives in MEMORY.md lines, memory stubs, open-PR states, and
   draft goal files — four places that drift. New tooling should *render*
   existing state, not mint another copy (this was the verdict on
   project-journal's `projects/*.md`).
3. **Push, not poll.** The background-task contract (task-notifications,
   Monitor, the guard hook) exists so nothing requires "status?" polling.
   The same must hold one level up: Daniel should be paged, not have to
   sweep dashboards.
4. **Degradation tolerance.** Daemon death must not kill workers
   (anti-flightdeck invariant); relay pods self-heal; workers are
   idempotent-resume. Any command-center component must fail without taking
   the work down with it.
5. **Legible to agents, not just to Daniel.** State is markdown in git
   precisely so agents can read/write it and Daniel can diff/veto it
   ("memory is a folder of markdown files I can read" — DESIGN.md). Rules
   out: opaque DBs, SaaS boards that agents can't cheaply consume.
6. **Attention spent at the top of the ladder.** Daniel's touchpoints should
   be direction-setting and review — not supervision, not status collection,
   not resource babysitting. Automation climbs one rung at a time as trust
   is earned (propose-only → gated dispatch, per-goal `automation` flags).
7. **Durable and versioned.** Everything that matters survives session
   death and lives in git (concierge tasks as files, goals as files,
   memory as files). Ephemeral views (dashboards) are regenerable.

---

## Layer-by-layer: implementation and pain

### 1. Direction — 🔴 stuck in review

`goals/` registry + propose-only `/goal-review` shipped as **PR #112 on
2026-07-17 and has sat unmerged for a month**, with the seeded goal file
still carrying a DRAFT banner awaiting Daniel's edit. Net effect: the
direction layer *exists but isn't operating* — dispatch decisions still live
in Daniel's head and get made ad hoc per session. The ladder
(groundskeeper → planner cron → gated dispatch) can't start climbing until
the first rung is merged.

**Pain:** the layer designed to reduce Daniel-dependence is itself blocked
on Daniel — and nothing surfaced that irony until this doc. That's a layer-5
failure compounding a layer-1 failure.

### 2. State — 🟡 works, but self-reported and drifting

`MEMORY.md` is genuinely good: one line per thread with status, per-project
stubs with detail, agent-maintained, git-versioned, weekly-consolidated into
wiki/. It is the de-facto project registry.

**Pain:** (a) it's *self-reported* — a thread's line says whatever the last
session wrote, and threads that end abruptly go stale silently (several
stubs carry "not yet PR'd" / "Slack TL;DR not yet posted" flags of unknown
current truth). (b) Status facts are duplicated across memory, PR states,
and goal drafts with no reconciliation. (c) "blocked-on-Daniel" items are
buried *inside* stubs (e.g. bellhop-instant-clusters lists three) rather
than aggregated anywhere.

### 3. Execution — 🟢 the strong layer

Concierge (durable gated tasks, trees-and-leaves delegation, waiting-state,
budget caps), stagehand (declarative DAGs + live dashboards), bellhop
(ephemeral pods), arch2 (fleet runs). Hard-won invariants are encoded:
externally-checked gates, no-detach background contract, workers survive
daemon death, results-not-artifacts gating. This layer has absorbed the most
iteration and it shows.

**Pain:** mostly residual sharp edges (pool.ask 0-turn bug; waiting-state
interactions), plus the fact that *entry* into this layer is manual — there
is no planner feeding it (layer 1) and no unified view of what it's running
(layer 4 covers live terminals but not the pool's task tree).

### 4. Observability — 🟡 excellent *live*, absent *historical*

Live is well covered: foyer (terminals + plots + notes at a stable URL,
"already super useful"), lobby (one hub URL for all serving apps), stagehand
dashboards (per-flow), databrowser (per-result-set), session-rundown
(on-demand Slack digest of active sessions).

**Pain:** (a) **No historical/activity layer at all** — nothing answers
"which threads actually got worked on this week, which are dormant, what
sessions belong to no known thread?" This is precisely the hole
project-journal's transcript scanner fills (observed activity, dormancy
flags, unfiled-session inbox) — its scanner is worth adopting; its registry
half is redundant with layer 2. Matching must key on worktree-branch →
memory-slug (± concierge task metadata), not cwd — our many-threads-one-repo
layout defeats cwd matching. (b) Views are *federated but not unified*:
foyer deliberately sits outside lobby; the concierge task tree has no web
view; "one glanceable page" doesn't exist.

### 5. Attention routing — 🔴 the weakest layer

What exists: task-notifications reach whichever session spawned the work
(session-scoped, dies with it); concierge `blocked` state works but nothing
*pushes* it to Daniel — he discovers blocked tasks by asking; Slack posts
are manual and convention-driven.

**Pain:** (a) **flare — the universal agent→Slack distress channel — is
designed (arsenal #36) but unbuilt**, so pod scripts, arch2 workers, and
crons have literally no way to page Daniel. (b) There is no **"waiting on
Daniel" inbox**: blocked concierge tasks, DRAFT files awaiting edit,
month-old PRs, and blocked-on-Daniel bullets in memory stubs are four
disjoint queues, none of which push. The single highest-leverage missing
artifact in the whole system is arguably one aggregated, pushed,
waiting-on-Daniel list.

### 6. Review & integration — 🔴 the actual bottleneck

The mechanics are solid (pinned-main + worktrees, wrap-up standard,
reportly-linted reports, lab-notes site). The throughput is not: **8 PRs
open, oldest from 2026-06-29**, including the direction layer itself. Agents
generate reviewable units faster than Daniel reviews them, and unreviewed
work silently blocks its downstream (follow-ups parked, worktrees lingering,
goals inert).

**Pain:** review debt is invisible-by-default (no aging view, no push at
threshold) and unassisted (no pre-chewed review brief per PR: what changed,
what to check, what it blocks). Both are cheap to build; neither exists.
Worth an explicit policy decision too: which PR classes need Daniel at all
vs. agent-review + auto-merge with veto window.

### 7. Resources — 🟡 patched, not principled

Concierge enforces a daily USD cap; bellhop has TTLs; the pod-audit cron
(weekly, propose-only) catches leaked pods.

**Pain:** all safeguards are *reactive* — the audit exists because pods
leaked; the gate-on-results rule exists because a worker orphaned a pod. No
single view answers "what is currently burning money and which thread owns
it"; bellhop pod-side TTL is an open issue; RunPod balance has itself been
a silent blocker (H200 benchmark stalled on top-up — again a layer-5 gap:
nothing paged Daniel that work was blocked on money).

---

## Gap analysis → build order

Ranked by leverage per unit effort:

1. **Waiting-on-Daniel inbox (layer 5+6).** One rendered list aggregating:
   blocked/waiting concierge tasks, open PRs with age, DRAFT-flagged files,
   `blocked-on-Daniel` markers in memory stubs (make that a grep-able
   convention), low-balance/resource blocks. Pushed to Slack on change or
   threshold, served via lobby. Kills the biggest failure mode found while
   writing this doc: work-blocked-on-Daniel that Daniel doesn't know about.
2. **Build flare (layer 5).** Already designed, small, unblocks every other
   push behavior; the inbox above can use it as transport.
3. **Activity journal (layer 4).** Adopt project-journal's scanner idea as
   an arsenal package: transcripts + git + concierge records → per-thread
   sparklines, dormancy flags, unfiled-session inbox, rendered over the
   *memory* registry (no second registry). Feeds memory-consolidate ("these
   6 sessions matched no thread").
4. **Merge PR #112 and start the direction ladder (layer 1).** Requires
   Daniel to edit the DRAFT goal — a 30-minute unblock that activates a
   whole layer. Should be item #1 in the new inbox.
5. **Review-debt tooling (layer 6).** PR-aging in the inbox + an agent-made
   review brief per PR; then decide the auto-merge-with-veto policy.
6. **Resource ledger (layer 7).** Fold pod-audit's inventory into a
   continuously rendered "what's burning money, owned by which thread" view;
   page through flare instead of weekly propose-only issues.

The composite vision, one sentence: **markdown-in-git remains the single
source of truth per layer; a small set of renderers turn it into one
glanceable hub page plus one pushed inbox; and every autonomous component
can page Daniel through one sanctioned channel — so Daniel's only jobs are
setting direction and reviewing work.**

---

## Non-goals

- A single monolithic app. The unix-y federation (small tools + lobby) is
  working; the missing piece is aggregation views, not consolidation.
- Real-time control from the hub beyond what foyer already gives (terminals
  are the control surface; concierge `pool.msg` is the mailbox).
- SaaS project-management adoption (Linear stays a floated option for goals
  mirroring only; files remain source of truth — see desideratum 5).
