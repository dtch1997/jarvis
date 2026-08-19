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
repo is that command center's durable state — and deliberately *only* the
meta-level: object-level work lives in dedicated repos under the `repos/`
pattern (README), and jarvis keeps direction, findings, conventions, and
pointers. The test for what belongs here: does it make every future
project better, or just one?

We've been building it piecemeal (concierge, foyer, lobby, goals/, memory,
flare…); this doc names the pattern, states the desiderata, maps each layer
to its current implementation, and lists the pain points honestly. The
immediate trigger was evaluating `dtch1997/project-journal` as a candidate
piece; the diagnosis below says which hole it actually fills.

The user-facing distillation of this doc — the five surfaces Daniel
touches and the guarantee each owes him — is
[`docs/interface-contract.md`](interface-contract.md).

**The core framing.** The scarce resource is Daniel-attention. Every layer
exists either to (a) let work proceed without it, or (b) spend it at maximum
leverage when it *is* needed. A good command center is therefore mostly not a
dashboard — it's a contract about where truth lives, how work gets permission
to run, and how the system asks for help.

---

## Two operating modes

*(Added 2026-08-15 from Daniel's design notes.)* The command center serves
two genuinely different use cases, and conflating them causes design errors:

- **Copilot mode** — Daniel is present and coworking. Synchronous, low
  latency, trust is per-exchange because he's watching. The surfaces are
  interactive sessions, cowrite (shared document), foyer terminals,
  artifacts. Attention routing is trivial (he's already here); review
  happens inline; spec rigor can be conversational.
- **Full-auto mode** — Daniel tasks the system and leaves. Asynchronous,
  throughput-oriented, trust must be *structural* because nobody is
  watching: well-specified tasks ([experiments-need-spec]), externally
  checked gates, hard budgets, idempotent-resume workers. The surfaces are
  concierge, arch2 fleets, stagehand, crons. Attention routing is critical
  (push, not poll); review arrives as a PR queue; resource safeguards carry
  the whole load.

Three design implications:

1. **Every tool and flow should know which mode it serves.** Most of our
   stack already sorts cleanly (cowrite/foyer = copilot; concierge/arch2 =
   full-auto); ambiguity is where the pain lives — e.g. an interactive
   session that quietly backgrounds hours of work is copilot-mode trust
   carrying full-auto-mode risk.
2. **The mode boundary is where work gets lost.** A copilot session's output
   must still land in the durable state layer (wrap-up discipline, memory,
   PR) or it evaporates — the power-concentration prototype sat invisible in
   a worktree for exactly this reason. Symmetrically, full-auto output
   re-enters copilot mode through review, which is why the review layer
   being the bottleneck hurts twice.
3. **Mode sets the defaults**: interrupt budget (copilot = interrupt freely;
   full-auto = flare/inbox thresholds), spec rigor (conversational vs
   gate-checked), and how strictly the no-underspecified-experiments rule
   binds.

---

## Threads — the bottom-up spine

*(Added 2026-08-17 from Daniel's design notes; philosophy update.)*

**The model.** The unit of work-state is the **thread**, and threads are
built bottom-up from observation: every transcript (interactive session,
concierge worker, arch2 worker) yields an extracted **summary**; related
summaries are grouped into threads with a distilled note on top. Threads are
**recursive in shape**: a single session plus its surrounding context is the
smallest thread, and higher-order threads are woven from lower ones. In
practice this is a links-based tree of ~2–3 levels — session → project
thread → goal — with the same shape at every level (constituent summaries +
a distilled note), not unbounded nesting machinery.

**Philosophy update: direction is bidirectional.** The original framing had
direction flow top-down only (Daniel states goals; agents execute against
them). Daniel's stated position (2026-08-17): **bottom-up direction
discovery is equally valid** — emergent patterns in accumulated work
(recurring themes across summaries, follow-ups that keep resurfacing,
clusters of unfiled sessions) are a legitimate origin for new threads *and
new goals*. Agents are sanctioned to **generate threads automatically**,
without pre-approval. This completes draft-and-veto rather than amending
it: agents propose and operate at every level, *including inventing the
levels*; Daniel's authority is exercised as cheap lazy veto —
delete/rework a thread he doesn't like — never as a prerequisite. The
process will be refined through practical use, not designed up front.

**Derived vs. curated — the desideratum-2 resolution.** Extraction creates
derived facts ("what happened"); intent ("what it means, what's next") is
not derivable from transcripts. To avoid a second registry (the
project-journal verdict): thread identity keys on the existing memory
registry (one thread = one memory slug), the curated thread note *is* the
memory stub, and extraction feeds it a machine-drafted activity view
(last-touched, session list, dormancy) that agents never hand-edit.
Bottom-up supplies observation; the curated layer keeps meaning; no fact
lives twice.

**The counterweight.** Emergent direction discovers *momentum*, and momentum
favors what's easy to advance, not what matters most. The checks are the
interestingness rubrics (goals/) and the portfolio coverage view — threads
serving no goal, goals with no active threads — plus explicit prune
candidates, since pruning is where Daniel's veto attention has the most
leverage.

MVP spec for the extraction pipeline + summary dashboard:
[`docs/threads.md`](threads.md).

**The inbound counterpart — thought capture.** *(Added 2026-08-17.)*
Threads observe what *agents* did; the symmetric gap is what *Daniel*
captures — thoughts landing in Todoist, voice memos, and Slack lab-notes,
today three silos nothing consumes. The `mailroom` pipeline (same shape:
ingest → triage → route, draft-and-veto) drains those surfaces onto the
existing spines — threads notes, Todoist projects, goal files, the papers
queue — with loop-closure marks at each source and a daily digest as the
veto surface. Standing decisions: Todoist is capture-only and drained to
zero; voice memos transcribe via Parakeet; Slack ingestion is
multi-channel by config (MVP: `#lab-notes-daniel`); mailroom stays
separate from threads for now, with a shared Obsidian-style vault as the
expected future convergence. MVP spec:
[`docs/thought-capture.md`](thought-capture.md).

**The intentional counterpart — the thread launcher.** *(Added
2026-08-18.)* Scan/weave build threads *observationally*, after the fact;
the launcher is the intentional birth of a thread: a text box + send that
instantly (<100ms) creates a thread from a declared intent, chooses the
operating mode at entry (full-auto default → concierge; copilot → seeded
tmux/foyer session), auto-attaches to an existing slug or mints a
candidate thread, stamps the slug into everything it spawns (demoting
heuristic weave to a safety net), and enforces a termination contract —
every launched thread reaches a terminal note or gets paged about. This
is the "planner feeding layer 3" gap entered from the direction the pain
is felt: message-inward, not goals-downward. MVP spec:
[`docs/thread-launcher.md`](thread-launcher.md).

---

## The board — the auto-mode front page

*(Added 2026-08-18 from Daniel's design notes; UX decision.)*

**The stated ambition** (Daniel, 2026-08-18): say "let's do XYZ" and have
assurance it gets done — a proper exit criterion, wrapped up appropriately,
notified later with the deliverables. The surface for that ambition is the
**thread board**: a responsive web table where **each row is a thread** and
the columns are **Prompt | Goal | Status** — super-fast row add (the
launcher's <100ms send contract), an agent-drafted Goal cell (deliverables +
exit criteria, backed by an externally-checked gate, inline-editable as the
veto surface), and a machine-derived Status column running the termination
contract. Full spec: [`docs/thread-board.md`](thread-board.md); substrate:
the thread launcher ([`docs/thread-launcher.md`](thread-launcher.md)).

Three design consequences:

1. **The board is the go-to interface for full-auto mode, replacing tmux.**
   This resolves the mode-surface ambiguity cleanly: foyer/tmux remain the
   copilot surfaces (presence, terminals); the board is where auto-mode work
   is fired and glanced at. It is the "one glanceable page" that layer 5's
   pain list said didn't exist — for work-threads specifically.
2. **The internal loop per row is prompt → propose → execute → monitor**,
   with propose under draft-and-veto: the router drafts the goal/gate and
   proceeds; Daniel redirects by editing the cell, never by pre-approving.
3. **Transports are renderers.** A row's history is a transport-agnostic
   event feed; the web board is the first renderer. Slack is **shelved**
   (Daniel, 2026-08-18, superseding the same-day Slack-first framing) but
   maps cleanly later — one JARVIS thread ↔ one Slack thread — as a second
   renderer of the same feed, not a second data model.

---

## The layer model

Seven layers, grouped into a **core work loop** and a **support plane**
(grouping per Daniel, 2026-08-15). The core four form a closed cycle —
direction decides against state, execution produces artifacts, review
integrates them into truth, which updates state and refeeds direction. The
support plane never moves work forward; it watches the loop, pages Daniel
when it stalls, and bounds its spend. Each layer answers one question with
one source of truth.

**Core work loop:**

| # | Layer | Question it answers | Current implementation | Health |
|---|-------|--------------------|------------------------|--------|
| 1 | **Direction** | What *should* be worked on? | `goals/` registry + propose-only `/goal-review`, **draft-and-veto ownership** (merged 2026-08-15, five goals) | 🟡 |
| 2 | **State** | What threads exist, and what's their status? | `memory/MEMORY.md` + per-project stubs; wiki/ for findings | 🟡 |
| 3 | **Execution** | How does work actually run? | concierge pool, arch2 fleets, stagehand DAGs, bellhop pods, interactive sessions | 🟢 |
| 4 | **Review & integration** | How does finished work become truth? | PRs on pinned-main + worktrees, "wrap up" keyword, lab-notes, reportly | 🔴 |

**Support plane:**

| # | Layer | Question it answers | Current implementation | Health |
|---|-------|--------------------|------------------------|--------|
| 5 | **Observability** | What is happening / has happened? | foyer (live terminals), lobby hub, stagehand dashboards, databrowser, session-rundown | 🟡 |
| 6 | **Attention routing** | How does the system ask for Daniel? | flare (universal push, shipped 2026-08-16) + desk (waiting-on-Daniel inbox + hourly sync cron), `BLOCKED-ON-DANIEL:` marker convention; Slack webhook still unconfigured (spool-only) | 🟡 |
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

### 1. Direction — 🟡 merged, now operating under draft-and-veto

`goals/` registry + propose-only `/goal-review` shipped as PR #112 on
2026-07-17 and **sat unmerged for a month** waiting on Daniel to author the
Daniel-owned sections — the layer designed to reduce Daniel-dependence was
itself blocked on Daniel, and nothing surfaced that irony until this doc.

**Resolution (2026-08-15, Daniel's call): direction never bottlenecks on
completed direction.** Ownership flipped to **draft-and-veto**
(`goals/README.md`): agents draft everything — Vision, rubrics, candidate
new goals — marked `agent-drafted, standing until Daniel edits`, and drafts
are *immediately operative*; Daniel edits/vetoes lazily. The only calls that
wait for him are the safety knobs: `automation: dispatch` and real budgets.
Registry merged with five goals (self-driving-jarvis + four Daniel-stated
2026-08-15: thesis, ARC WHEST post, power-concentration post, dogfight-rl
release).

**Remaining pain:** the ladder above the registry (groundskeeper cron,
planner-on-cron, gated dispatch) is unbuilt, and brainstorm quality is the
open bet — propose-only reviews only earn dispatch rights if the specs are
good.

**Update 2026-08-17 — direction is bidirectional** (see "Threads — the
bottom-up spine" above): goals may also be *discovered* bottom-up from
emergent patterns in accumulated work, drafted by agents as
`status: incubating` goals under the existing draft-and-veto provenance
rules. The thread pipeline's portfolio view (threads↔goals coverage) becomes
an input to `/goal-review`.

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
than aggregated anywhere. *(c) is now handled by `desk` (attention routing,
shipped 2026-08-16).*

**Planned fix for (a)** — the threads model (see "Threads — the bottom-up
spine"): activity facts get extracted from transcripts rather than
self-reported; the stub stays the curated thread note but its activity view
becomes machine-drafted. MVP spec: [`docs/threads.md`](threads.md).

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
(layer 5 covers live terminals but not the pool's task tree).

### 4. Review & integration — 🔴 the actual bottleneck

The mechanics are solid (pinned-main + worktrees, wrap-up standard,
reportly-linted reports, lab-notes site). The throughput is not: **8 PRs
open, oldest from 2026-06-29**, until 2026-08-15 including the direction
layer itself. Agents
generate reviewable units faster than Daniel reviews them, and unreviewed
work silently blocks its downstream (follow-ups parked, worktrees lingering,
goals inert).

**Pain:** review debt is invisible-by-default (no aging view, no push at
threshold) and unassisted (no pre-chewed review brief per PR: what changed,
what to check, what it blocks). Both are cheap to build; neither exists.
Worth an explicit policy decision too: which PR classes need Daniel at all
vs. agent-review + auto-merge with veto window.

### 5. Observability — 🟡 excellent *live*, absent *historical*

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
layout defeats cwd matching. *2026-08-17: this item has been generalized
into the threads model + summary dashboard — spec in
[`docs/threads.md`](threads.md).* (b) Views are *federated but not unified*:
foyer deliberately sits outside lobby; the concierge task tree has no web
view; "one glanceable page" doesn't exist. *2026-08-18: the thread board
(see "The board" above; spec `docs/thread-board.md`) is the designed answer
for work-threads — rows = threads, Status machine-derived, needs-you rows
pinned; build follows the launcher (PR #14).*

### 6. Attention routing — 🔴 the weakest layer

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

*Update 2026-08-17: both shipped 2026-08-16 — `flare` + `desk` (arsenal
#42/#46, jarvis #126; CLAUDE.md "Attention routing" is now canonical).
Residual: Slack webhook unconfigured (spool-only), polish issues arsenal
#43–#45.*

### 7. Resources — 🟡 patched, not principled

Concierge enforces a daily USD cap; bellhop has TTLs; the pod-audit cron
(weekly, propose-only) catches leaked pods.

**Pain:** all safeguards are *reactive* — the audit exists because pods
leaked; the gate-on-results rule exists because a worker orphaned a pod. No
single view answers "what is currently burning money and which thread owns
it"; bellhop pod-side TTL is an open issue; RunPod balance has itself been
a silent blocker (H200 benchmark stalled on top-up — again a layer-6 gap:
nothing paged Daniel that work was blocked on money).

---

## Gap analysis → build order

Ranked by leverage per unit effort. (Daniel confirmed 2026-08-15 that
attention routing — items 1–2 — is the high-value build.)

1. ~~**Waiting-on-Daniel inbox (layers 6+4).**~~ **DONE 2026-08-16 as
   `desk`** (jarvis #126). One rendered list aggregating:
   blocked/waiting concierge tasks, open PRs with age, DRAFT-flagged files,
   `blocked-on-Daniel` markers in memory stubs (make that a grep-able
   convention), low-balance/resource blocks. Pushed to Slack on change or
   threshold, served via lobby. Kills the biggest failure mode found while
   writing this doc: work-blocked-on-Daniel that Daniel doesn't know about.
2. ~~**Build flare (layer 6).**~~ **DONE 2026-08-16** (arsenal #42;
   spool-only until the Slack webhook is configured). Already designed,
   small, unblocks every other push behavior; the inbox above uses it as
   transport.
3. **Thread pipeline + summary dashboard (layers 5+2).** *(Generalized
   2026-08-17 from the "activity journal" item; MVP spec:
   [`docs/threads.md`](threads.md).)* An arsenal package (`threads`) that
   extracts per-session summaries from transcripts, weaves them into
   threads keyed on the memory registry (worktree-branch → slug ±
   concierge metadata; no second registry), auto-drafts candidate threads
   for unmatched clusters, and serves the dashboard via lobby: per-thread
   activity + last-touched, dormancy flags, unfiled-session inbox,
   threads↔goals coverage. Feeds memory-consolidate and /goal-review.
   *Extended 2026-08-18: shipped in stages — threads v0.2 + note/pickup
   (live), thread launcher (PR #14), and the thread board
   (`docs/thread-board.md`) as the front page of this layer.*
4. ~~Merge PR #112~~ **DONE 2026-08-15** (draft-and-veto ownership). Next
   rung of the direction ladder: run `/goal-review` cycles and let agents
   brainstorm candidate goals at `status: incubating`.
4b. **Thread launcher (layers 3+1).** *(Added 2026-08-18, Daniel-approved;
   MVP spec: [`docs/thread-launcher.md`](thread-launcher.md).)* The
   intent→thread front door: text box + send instantly creates a thread,
   mode chosen at entry (full-auto default via concierge, copilot via
   seeded session), auto-attach to existing slugs, slug stamped at spawn,
   termination contract enforced. Fills the "entry into layer 3 is
   manual" gap from the message-inward direction.
5. **Review-debt tooling (layer 4).** PR-aging in the inbox + an agent-made
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
