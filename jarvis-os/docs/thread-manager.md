# Thread manager: workers behind threads, a switchboard in front — spec

*2026-08-18 · agent-drafted, standing until Daniel edits · completes the
threads trio: [`thread-launcher.md`](thread-launcher.md) owns birth,
[`thread-board.md`](thread-board.md) owns reading, this spec owns
**interaction** — plus the worker-binding model underneath both. Design
conversation Daniel + Claude 2026-08-18.*

## What this is

The copilot half of the threads model. The launcher already makes threads
operational for full-auto (intent → thread → gated concierge worker). This
spec makes them operational for *interaction*: every thread is **backed by
one or more workers** (resumable sessions), and Daniel talks to the system
through a single **top-level thread manager**.

Daniel's articulation (2026-08-18): each thread should be backed by one or
more workers (e.g. resumable sessions); there should be a top-level thread
manager used as the interface to interact with threads.

## Design decisions (Daniel, 2026-08-18)

Three calls made explicitly in the design conversation:

1. **Switchboard, not proxy.** The manager routes and attaches; it does
   not relay every copilot exchange. *Daniel flagged this as an explicit
   design choice with viable alternatives* (always-via-manager proxy;
   hybrid-by-depth where quick nudges route through the manager and
   sustained coworking triggers attach) — revisit if switchboard friction
   shows up in practice.
2. **Disposable workers over durable thread state, with a warm cache.**
   The thread's notes + memory stub are canonical; resumable sessions are
   an optimization. Workers may be interrupted or die at any time, so:
   - **Worker exit contract**: every worker dumps an informative tl;dr to
     the thread context on *any* termination — clean, interrupted, or
     killed (for kills, the sweep writes it post-hoc from the transcript).
   - **Transcript IDs are filed on the thread** at spawn, so the worst
     case is always recoverable by reading the transcript — and good
     tl;drs exist to make that worst case rare.
3. **Surface: chat pane backed by a tmux panel.** The manager runs as a
   long-lived tmux session (terminal-native, reachable via foyer); the
   thread board grows a chat pane that fronts the same session. One
   manager, two doors.

## The worker model

- **Thread = durable identity; worker = attachable compute.** This flips
  threads from observational (scan/weave reconstructs after the fact) to
  operational: the thread owns its workers, not the reverse.
- **Equivalence invariant**: a fresh worker hydrated from the thread's
  notes (`threads pickup`) must be able to continue the work. Resuming a
  cached session (`claude --resume` / `pool.ask`) is the warm path;
  pickup-from-notes is the cold path; both must stay equivalent. If
  continuing *requires* the old transcript, the exit contract was
  violated — that's the bug to fix, not a state to design for.
- **One or more workers**: parallel workers on one thread cooperate
  through the thread's state (notes, branch, artifacts), never through
  each other's transcripts. Trees-and-leaves delegation applies within a
  thread as it does in concierge.
- **Worker registry on the thread**: each spawn files `{session/task id,
  transcript path, mode, branch, started, status}` as thread metadata —
  this is what the manager reads to decide resume-vs-fresh, and what the
  board's row detail lists as "executor handles".

## The manager

A **switchboard**: thin, near-stateless, rehydrated from the registry and
pool state each turn. It holds no unique context — thread context lives in
threads, so manager death loses nothing (anti-flightdeck invariant).

**Verbs** (the manager's whole vocabulary — everything else belongs to a
thread's own worker):

- `spawn <intent>` — subsumes the launcher front door (`threads launch`).
- `status [slug]` — renders from observed state, same derivation rules as
  the board's Status column; never worker self-report.
- `attach <slug>` — drop Daniel into the thread's worker: resume the
  cached session if warm, else hydrate a fresh one from notes; surface it
  as a tmux window + foyer URL. The manager then gets out of the way.
- `detach` — **a defined event, not an absence**: triggers the worker's
  tl;dr note mechanically (the parking convention enforced, not relied
  on), updates the worker registry, returns Daniel to the manager.
- `msg <slug> …` — one-shot nudge to a running worker (`pool.msg`)
  without attaching.
- `park <slug>` / `prioritize <slug>` — thread-level state ops.

**Mode collapse**: copilot vs full-auto stops being a property of the
thread and becomes *"is Daniel currently attached."* Same worker, same
gates, same termination contract either way. The mode boundary the
command-center doc calls "where work gets lost" reduces to the detach
event — which now writes the note by construction.

## Non-goals (MVP)

- Proxy/hybrid routing (explicitly deferred, see decision 1).
- Slack as a manager door (standing decision from the board spec; the
  manager's event feed is the substrate a Slack renderer would consume).
- Multiple managers / multi-user.
- Cross-thread scheduling or priority beyond `prioritize` as metadata.
- Embedding terminals in the board — the chat pane fronts the manager
  only; attach still lands in tmux/foyer.

## Definition of done (MVP, gate-checkable)

1. Spawning a worker on a thread files its transcript ID + handles in the
   thread's worker registry (visible in board row detail).
2. Killing a worker mid-task and running `attach` produces a continuation
   that demonstrably used only thread state (cold path exercised in a
   smoke test, not just claimed).
3. `detach` writes the tl;dr note without being asked — verified by
   detaching a session that wrote nothing itself.
4. The manager tmux session survives a restart with no lost thread state,
   and the board chat pane round-trips a `status` and a `spawn` through
   it.
5. A worker that terminates uncleanly gets a post-hoc tl;dr from the
   sweep within one cycle, flagged as sweep-written.

## Build notes

Extends `threads` (registry, notes, launcher) + `concierge` (resume,
msg) + the board server; no new package. **Sequencing: after PR #14**
(launcher impl — the spawn/termination substrate) and alongside or after
the board MVP (the chat pane needs a board to live on; the tmux door can
ship first). Implementation is a concierge dispatch once this spec is
SG'd/edited; gate = the DoD above.
