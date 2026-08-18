# The morning routine

*(agent-drafted, standing until Daniel edits — 2026-08-18)*

Daniel's stated frame: he is mainly a **consumer of JARVIS software** — the
system runs overnight, and each morning he reads what happened rather than
operating the machinery. This doc sketches the morning surface. Patch notes
(shipped, see below) are the first component; the rest is proposed.

## Components

| when  | what | tool | status |
| ----- | ---- | ---- | ------ |
| 03:29 | nightly PR merge sweep (produces the morning's news) | `gazette sweep` | shipped |
| 08:05 | **patch notes** — merged / in the pipeline / waiting on you / anomalies | `gazette notes --flare` | shipped |
| 08:35 | **desk digest** — everything blocked on Daniel | `desk digest` → flare | live |
| 07:19 | threads scan+weave (activity dashboard stays fresh) | `threads` | live |
| —     | goal-portfolio pulse (weekly, not daily) | `/goal-review` | on demand |

Delivery today = flares (spooled; Slack once the webhook is configured —
BLOCKED-ON-DANIEL) plus lobby pages (`/a/threads/`, `/a/desk/`).

## Direction: one page, not four flares

The likely v2 is a single **morning page** (lobby app or emailed digest) that
composes, in reading order:

1. Patch notes (what changed without you — skimmable, one line per merge).
2. Veto window (the only items where reading has a deadline).
3. Waiting on you (desk items, ranked by age × importance).
4. Activity pulse (threads: which work-threads moved yesterday, which
   stalled).
5. Today (calendar + Todoist due — needs MCP plumbing; see mailroom spec for
   the capture direction).

Open questions for Daniel to veto/shape:

- Reading order above right? (Current guess: news → deadlines → asks →
  ambient.)
- Is 08:05 the right delivery time, and is one page/day the right cadence —
  or notes-on-demand with only the flare digest pushed?
- Should the veto window pause on days with no morning read (e.g. weekends),
  i.e. window measured in *patch-notes-delivered* rather than wall-clock
  hours?
