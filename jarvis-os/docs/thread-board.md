# Thread board: Prompt / Goal / Status — spec

*2026-08-18 · agent-drafted, standing until Daniel edits · builds on the
thread launcher ([`thread-launcher.md`](thread-launcher.md), impl PR #14)
and the threads dashboard; design conversation Daniel + Claude 2026-08-18*

## What this is

The **go-to interface for auto-mode work**, replacing tmux as Daniel's
default surface. A responsive browser UI: a table where **each row is a
thread** and the columns are **Prompt | Goal | Status**. Adding a row must
be *super fast* — the board is optimized for firing many threads back to
back, then glancing at how each is going.

Daniel's articulation (2026-08-18), which this spec serves:

> Given the prompt, figure out what would be good ways to make progress
> towards this, propose, and then execute on it, while giving me a good
> way to monitor.

That is the internal loop: **prompt → propose → execute → monitor**, with
propose operating under draft-and-veto (the proposal is immediately
operative; Daniel edits or vetoes lazily, and clarification is async,
never a reason to hold the intent).

Standing decision (2026-08-18): **Slack transport is shelved for now.**
The web board comes first. The row model must stay transport-agnostic —
a row's history is an event feed the web board renders; a Slack thread is
a *future* second renderer of the same feed (a JARVIS thread maps cleanly
onto a Slack thread), not a different data model.

## The three columns

### Prompt — what Daniel said

The intent text, verbatim. Row creation *is* `threads launch`: the top of
the table is a text box; Enter appends a row instantly (optimistic render;
the send contract already guarantees a durable intent record in <100ms
with no model calls). No modal, no required fields beyond the text.
Optional per-row affordances at add time: slug autocomplete (pin the
thread), mode toggle (full-auto default; copilot is the deliberate
choice).

Observed threads (born from scan/weave, not the launcher) also appear as
rows; their Prompt cell is the thread's distilled title, visually marked
as observed rather than launched.

### Goal — deliverables + exit criteria, drafted then edited

The Goal cell answers: *what artifact(s) will exist, and what externally
checkable condition means done?* It is **agent-drafted** from the prompt —
this is the launcher router's interpretation note (reading + assumptions +
chosen gate) elevated from a buried thread note to a **first-class,
inline-editable field** on the intent record.

- Draft-and-veto: the drafted goal is immediately operative; execution
  does not wait for Daniel to read it.
- **Inline edit = the veto/redirect surface.** Editing before the executor
  spawns re-specs the task (router re-derives the gate from the edited
  goal). Editing while running delivers the edit to the worker
  (`pool.msg`) and flags the row so the discrepancy is visible; the gate
  is re-derived only if the executor hasn't passed it yet.
- Gates follow house rules: externally checked, results-not-artifacts for
  compute. The gate (machine-readable) and the goal prose stay linked —
  the cell shows the prose, expands to show the literal gate.

### Status — machine-derived, never self-reported

The monitoring column. Every value is derived from observed state — the
same principle as concierge gates (desideratum 1: observed truth beats
self-report):

- **Lifecycle**: `routing → spawning → running → result | blocked |
  failed` (the launcher's termination contract verbatim; terminal states
  come from the gate settling / pool state, not the worker's report).
- **Running** rows show live signal: concierge status + attempt + cost so
  far, last activity timestamp, and a link to the deepest live view
  available (stagehand dashboard for flows, foyer terminal for copilot
  rows, task log tail otherwise).
- **Terminal** rows show the payoff inline: `result` renders the
  deliverable pointers (PR, report URL, databrowser link, GCS path) right
  in the cell; `blocked` renders the actual question for Daniel;
  `failed` renders what broke.
- **Contract violations** (dormant past deadline with no terminal note —
  the termination sweep PR #14 already runs) render as loud rows, not
  just desk items.

Row click-through opens the thread detail: full note history,
interpretation, executor handles, linked sessions.

## Board behavior

- **Sort: needs-you first.** `blocked` and contract-violation rows pin to
  the top (same deadline-first principle as the morning edition), then
  running by recency, then terminal. Terminal rows auto-collapse into an
  archive section after N days (config) — the board stays glanceable at
  dozens of threads.
- **Responsive**: usable from the phone; row add and status glance are
  the two interactions that must be excellent.
- **Served via lobby** (`/a/threads/` — this *is* the threads dashboard's
  front page now; the launcher pane and board merge into one surface).
  Board reads are cheap renders of the spool + pool state; no model calls
  on page load.
- **Veto affordances** carried over from the launcher pane: detach /
  merge-into-thread per row, candidate-thread delete.

## Internal loop (per row)

1. **Accept** (<100ms): durable intent record, optimistic row.
2. **Propose** (async, seconds): router resolves the slug, drafts the
   Goal cell — approach, assumptions, deliverables, gate — and records
   it on the thread. Proceeds without confirmation.
3. **Execute**: full-auto → concierge with the drafted gate (fleet-scale
   stays an escalation a worker makes, not a launch mode); copilot →
   tmux + worktree + foyer URL in the Status cell.
4. **Monitor**: Status column derives from pool/gate/monitor state;
   blocked pages through desk/flare as today; terminal note lands in the
   row, the thread, and the morning edition's "terminated since
   yesterday".

## Definition of done (MVP, gate-checkable)

1. Row add: text → Enter → row visible optimistically; intent durable in
   <100ms (existing `threads launch --check` covers the accept path).
2. Goal cell populates asynchronously with the drafted
   deliverables + exit criteria; the underlying gate is attached to the
   spawned task.
3. Editing a Goal cell pre-spawn changes the gate the executor receives
   (demonstrated end-to-end); post-spawn edit lands as `pool.msg` and
   flags the row.
4. Status transitions are observed-state-derived; a settled gate flips
   the row to `result` with deliverable pointers rendered inline, with
   no worker-authored status text anywhere in the column.
5. `blocked` and contract-violation rows sort to the top and are visually
   distinct.
6. Board is the default page at the lobby threads URL, responsive on
   mobile, zero model calls per page load.
7. Observed (non-launcher) threads appear as rows without breaking 1–6.

## Non-goals (MVP)

- **Slack transport/projection** — shelved (standing decision above); the
  event-feed row model is the only concession made for it now.
- Editing Prompt cells (a prompt is a record; redirect via Goal edit or a
  new row).
- Priority/scheduling across rows; budgets beyond concierge caps.
- Replacing foyer for copilot sessions — the board links to terminals,
  it doesn't embed them.
- Auth/multi-user beyond lobby's existing boundary.

## Build notes

Extends the `threads` package (dashboard + server + launch), no new
package. **Merge order: after PR #14** (launcher impl — this spec's
substrate) and mindful of PR #11 (package move to `jarvis-os/packages/`).
Implementation is a well-shaped concierge dispatch once this spec is
SG'd/edited; gate = the DoD above driven by `threads board --check` +
dashboard smoke.
