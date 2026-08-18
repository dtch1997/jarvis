# Thread launcher: intent → thread — MVP spec

*2026-08-18 · agent-drafted, standing until Daniel edits · extends the
threads model in [`command-center.md`](command-center.md) and
[`threads.md`](threads.md); design conversation Daniel + Claude 2026-08-18*

## What this is

The **intentional birth of threads**. Today the `threads` tool is entirely
observational: threads are reconstructed after the fact by scanning
transcripts and heuristically weaving them onto memory slugs. The launcher
adds the other direction — a thread exists *first*, as a declared intent,
and work accrues to it:

```
text box + send ──accept──▶ intent record ──route──▶ thread (slug) ──spawn──▶ executor
   (<100ms, durable)          (async, ~seconds)                  (copilot | full-auto)
```

Motivating UX (Daniel, 2026-08-18):

- **Decouple intention from implementation.** "How this gets answered" —
  one agent or a fleet, five minutes or five days — is an implementation
  detail the sender never specifies.
- **Unbounded parallelism.** Fire as many threads as desired, back to
  back, with no waiting on any previous thread; each is assured to
  eventually terminate (see the termination contract below).
- **Thread = the atomic primitive of work** (a chain of thought). Mode —
  copilot vs full-auto (`command-center.md`, "Two operating modes") — is
  chosen at thread entry.
- **Responsive, elegant UI**: a text box and a send button; send instantly
  creates a thread.

## The send contract

Send does exactly one synchronous thing: persist a durable **intent
record** (ULID-keyed, in the `~/.threads/` spool) and return a receipt.
Target <100ms; no model calls, no network beyond localhost. The intent
appears on the dashboard immediately.

Everything else is asynchronous and lands **on the thread**, never back at
the sender:

1. **Route** (target <10s): resolve the intent to a slug — see Router.
2. **Spawn**: start the executor for the chosen mode.
3. **Failures**: a route or spawn failure is written to the thread as a
   note and flared (`--sev warn`); it must never be silent.

## Router — slug resolution

Standing decision (Daniel, 2026-08-18): **attaching to an existing slug is
automatic** — no confirmation step.

1. If the sender pinned a slug (optional `slug` field / CLI flag /
   autocomplete in the UI), use it.
2. Else match the intent text against the registry (`MEMORY.md` index +
   candidate threads), same machinery as `weave`'s `candidate_slugs`
   pass: one cheap model call, accept only slugs that exist. A confident
   match → attach; the intent becomes a new note on that thread.
3. Else **mint a candidate thread**: kebab-case slug drafted from the
   intent, intent text as note zero — exactly what `threads note
   <new-slug>` does today. No second registry: candidate threads live in
   the spool until memory-consolidate promotes them (desideratum 2).

Wrong attachments are handled by veto, not pre-approval: **detach /
merge-into-thread are one-click actions on the dashboard**, same spirit as
candidate-thread delete. (Merge tooling is in-scope for MVP because
instant creation will fragment — five threads that are really one project
is the predictable failure mode.)

The router also drafts its **interpretation** of the intent (reading +
assumptions + chosen gate) as a note on the thread and *proceeds* —
draft-and-veto applied to interpretation. It flares only when genuinely
stuck; clarification is async, never a reason to hold the intent.

## Modes

**Full-auto is the default** — the launcher exists to decouple, and
copilot is the mode that spends Daniel's presence. Copilot is the
deliberate choice (a toggle next to send).

- **Full-auto** → `pool.submit` (concierge) with the intent + the router's
  interpretation as the spec seed. The router drafts the gate per house
  rules (externally checked; results-not-artifacts for compute). The
  concierge tid is recorded on the thread.
- **Copilot** → spawn a tmux session running `claude` seeded with the
  intent, in a fresh worktree on a dedicated branch, and hand back the
  terminal (foyer URL) as a note on the thread. Daniel joins when ready;
  until then it idles after initial context-gathering.

## Deterministic weave — stamp the slug at spawn

Launcher-born work never relies on heuristic matching. The launcher stamps
thread identity into everything it spawns:

- `THREADS_SLUG=<slug>` in the executor's environment (concierge spec env
  / tmux session env);
- the worktree branch named `<slug>/<short-ulid>` where a worktree is
  created;
- a synthetic `threads note` (note zero) carrying the session linkage.

`threads weave` gains a pass **before** all heuristics: a session whose
metadata carries a launcher stamp maps to its slug with no model call.
Target: **100%** deterministic match for launcher-born sessions;
scan/weave heuristics demote to the safety net for work entering through
other doors.

## Termination contract

Every launched thread must reach a **terminal note**: `result` (the
deliverable + pointers), `blocked` (a question for Daniel — surfaces via
desk/flare), or `failed` (what broke). Enforcement is structural, not
hoped-for:

- Full-auto: the concierge gate settling writes the terminal note
  (result on pass; failed on exhaustion); `blocked` maps from the pool's
  blocked state.
- Copilot: the session's wrap-up/park writes it (existing conventions);
  an abandoned copilot thread is caught by the dormancy sweep.
- **A launched thread that is dormant (default 3 days) with no terminal
  note is a contract violation** — the dashboard flags it and it pages
  through desk, distinct from ordinary thread dormancy.

Read side comes free: terminal notes surface in the thread table (the
dashboard becomes the results inbox), and the morning edition picks up
"threads that terminated since yesterday".

## Surfaces

One door, many transports:

- **Endpoint**: `POST /launch {text, mode?, slug?}` on the threads server
  (the same process behind `threads serve`).
- **CLI**: `threads launch "<text>" [--copilot] [--slug <slug>]` — same
  code path.
- **Web UI**: a launcher pane on the existing lobby-served dashboard —
  text box, mode toggle (default full-auto), optional slug autocomplete,
  send. Must feel instant (optimistic render on accept).
- **Future transports** (non-goal for MVP): mailroom routes a Slack
  message / Todoist capture into the same endpoint, making "message in
  Slack" and "send in the launcher" indistinguishable to the system.

## Storage

`~/.threads/` spool, alongside the existing layout: `intents/<ulid>.json`
(the durable send record: text, mode, timestamps, resolved slug, executor
handle, terminal state). Thread notes stay in `notes/<slug>/` as today.
No git-versioning in MVP (same posture as the rest of the spool).

## Definition of done (MVP)

Gate-checkable:

1. `threads launch "test intent"` returns in <100ms with a ULID; the
   intent is on the dashboard on next render.
2. Router demo: one intent auto-attaches to an existing slug, one mints a
   candidate thread; both outcomes visible on the dashboard with the
   interpretation note.
3. Full-auto path: a launched intent becomes a settled concierge task
   whose terminal note (with artifact pointers) is on the thread — gate
   settling wrote it, not the worker's self-report.
4. Copilot path: a launched intent yields a live tmux session seeded with
   the intent, slug-stamped, reachable via the foyer URL on the thread.
5. Weave: launcher-born sessions match their slug 100% deterministically
   (no model call), verified by `threads weave --check`.
6. Termination sweep: an artificially-aged intent with no terminal note
   is flagged and produces a desk item.
7. Launcher pane live behind lobby; URL delivered to Daniel.

## Non-goals (MVP)

- Mailroom/Slack transport (future; the endpoint is shaped for it).
- Fleet-scale executors (arch2) as a launch mode — full-auto covers the
  need via concierge; a fleet is something a worker escalates to.
- Replacing scan/weave — the observational layer remains the safety net
  and the only coverage for non-launcher work.
- Priority/scheduling across threads; budgets beyond concierge's existing
  caps.
- Auth/multi-user (lobby's existing access model is the boundary).
