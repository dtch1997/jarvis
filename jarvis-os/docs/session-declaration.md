# Session self-declaration

**Status:** convention live (2026-09-14, PR dtch1997/jarvis#220). Direction from
Daniel: "JARVIS threads should declare themselves at initialization and we
should have conventions for logging which make it easy to identify which
sessions are open." Memory: `session-self-declaration`.

## Problem

A session's identity used to be split across four stores keyed three ways:
the harness registry (`~/.claude/sessions/<pid>.json`: alive, session id,
tmux pane, a *derived* name like `jarvis-os-c0`), the statusline flags
(`~/.claude/statusline/sessions/<sid>.json`), threads notes
(`~/.threads/notes/<slug>/`), and the transcript (whose mtime means nothing:
housekeeping records keep touching it for days). Answering "which of my 14
sessions can I close?" took a transcript review per session.

## The convention in one sentence

Every thread of work declares itself at start with a thread slug, and every
session-level event after that is logged under the session id, so "what is
open and what does each one still owe" is a query (`threads sessions`), not
an investigation.

## 1. Identity

The key is the **harness session id**, never the pane or PID. `/clear` gives
a pane a new session id, so a cleared pane is a new session and gets a new
declaration; the previous one is marked superseded with a pointer forward,
so the pane's history is a chain.

## 2. Declaration

First action of a session:

```
threads declare <slug> "<one-line intent>" [--kind interactive|concierge|cron|subagent]
```

Writes `~/.threads/sessions/<session-id>.json`:

```json
{"session_id": "...", "slug": "negtext-modern", "intent": "P2 ablations + 1.7B/4B arms",
 "kind": "interactive", "pane": "jarvis-3:@2.%2", "cwd": "...", "branch": "negtext-modern",
 "declared_at": "2026-09-14T07:00:00+00:00", "supersedes": null}
```

Side effects (best-effort): rename the tmux window to the slug; set the
statusline topic row to `slug — intent`. The harness's own session name is
left alone (no supported write path). Slug = memory-stub name, or a new
kebab-case name that seeds a candidate thread (same rule as `threads note`).
Re-running `declare` re-points a pivoted session (`redeclared` event, old
slug kept as `previous_slug`). `threads declare --show` prints the current
declaration and last events.

## 3. Event log

`~/.threads/sessions/<session-id>.events.jsonl`, one JSON line per event
(`{"t": ..., "event": ..., ...}`): `declared`, `redeclared`, `resumed`,
`compacted`, `turn_ended`, `note`, `superseded`, `closed`. Statusline flags
stay in their own file (the statusline package cannot depend on threads);
`threads sessions` reads them directly. PR links and artifact publishes are
read from the transcript's own `pr-link` / `Artifact` records.

## 4. Hooks

One entry point, `threads hook`, registered in `jarvis-os/.claude/settings.json`;
stdin is the harness JSON, exit code always 0, errors swallowed
(`THREADS_HOOK_DEBUG=1` logs them to `~/.threads/sessions/hooks.log`).

| event | does |
|---|---|
| `SessionStart` source=`startup` | auto-declare from `$THREADS_SLUG` / `$THREADS_INTENT` / `$THREADS_KIND` when a launcher set them (concierge, cron, `threads launch`); else print the declare nag into context |
| `SessionStart` source=`clear` | supersede the pane's previous declaration; the nag names it ("this pane was on `X`") so the agent re-declares `X` or a new slug |
| `SessionStart` source=`resume` | log `resumed`, re-apply pane title, restate the declared thread |
| `SessionStart` source=`compact` | log `compacted` |
| `UserPromptSubmit` | one-line nag while undeclared; silent once declared. Never blocks a tool |
| `Stop` | log `turn_ended` — the last-real-activity timestamp |
| `SessionEnd` | log `closed`, stamp `closed_at` on the declaration |

## 5. The view: `threads sessions`

Deterministic and offline (~3 s for a dozen sessions). Joins the harness
registry (alive PIDs) × declarations × statusline flags × transcript
(`pr-link`, `Artifact` publishes, last real turn) × newest `turn_ended` ×
newest note on the slug or naming the session. One verdict per session,
first rule wins:

1. `busy` — mid-turn per the harness. Leave it.
2. `recent` — idle under `--idle-hours` (default 12). Leave it.
3. `needs-park` — idle with open flags, or a PR / artifact with no note since
   the last turn. Write the note (the detail block prints the command).
4. `closable` — idle, no flags, and a note newer than the last turn or
   nothing to account for. Send `/exit` to the pane.

`--json` for scripts; `--all` includes stale registry entries for dead PIDs;
`--include-self` lists the calling session. `threads board` (text and the
served page) shows the same rows at the top.

## 6. What does not change

`threads note` / `pickup` keep their meaning; memory stubs stay the durable
layer; the harness registry is only read. Undeclared sessions still work —
they show as `(undeclared)` with their derived name, which is the old state
of affairs made visible.

## Out of scope for the first cut

Auto-closing (closing stays a human `/exit`; `threads sweep` may act on
`needs-park` rows later), subagent declarations, migrating old statusline
flag files. Revisit after a week of watching the board.
