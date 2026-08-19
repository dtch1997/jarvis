# The morning routine

*(Daniel-approved 2026-08-18 — v2 design SG'd in session; implementation:
arsenal PR #73 + this PR)*

Daniel is mainly a **consumer of JARVIS software** — the system runs
overnight, and each morning he reads what happened rather than operating the
machinery. The morning surface is **one composed edition, read in ~2
minutes, closable the moment nothing needs him.**

## The edition

Delivered at **08:05 daily** as a single flare (Slack via the mailroom bot;
spooled to `~/.gazette/notes/YYYY-MM-DD.md` as the full page). Reading
order is deadline-first:

1. **Needs you** — the only section where reading has consequences, so it
   comes first. `requires-approval` PRs and desk items in one list, each
   with a copy-pasteable approve command ("sits until you act"). The
   `desk digest` is folded in here — no separate 08:35 flare.
2. **Anomalies** — mislabeled lanes, demotions, failing checks, sweep
   errors. The trust-calibration channel for the whole consumer-mode bet:
   loud when present, absent when clean.
3. **News** — an LLM pass groups the last 24h of merges into 3–6 narrative
   bullets, leading with capability changes phrased as "you can now …",
   PR refs trailing. The flat merge list lives in the spooled page, not the
   Slack message.
4. **Ambient tail** — pipeline items needing nothing, dashboards
   (`/a/threads/`, `/a/desk/`). Explicitly skippable.

A quiet morning is one line: *"Patch notes — quiet: N merged, nothing needs
you."* The routine only survives long-term if empty days cost five seconds.

## Versions replace veto windows (2026-08-19 rework)

The delay lane and its edition-counted veto window are **retired**. PRs
merge on green at the hourly sweep; the safety net moved post-merge:
nightly at 04:10 `gazette version cut` tags main as `vYYYY.MM.DD` and
`gazette version deploy` deploys it, so the box's behavior changes once
per night and every state has a name. Rollback is
`gazette version switch v<date>` (crons, CLIs, and CLAUDE.md roll back
together; the pin survives nightly deploys); `gazette version switch
latest` resumes tracking. The edition names the running version, and
behavior-shaping merges (CLAUDE.md, `ops/**`, packages) are annotated so
you know when a version is worth a second look. `requires-approval`
(money/credentials/external/destructive) is the one pre-merge gate left.

## Components

| when  | what | tool | status |
| ----- | ---- | ---- | ------ |
| :29 hourly | merge-on-green PR sweep | `gazette sweep` | live |
| 04:10 | version cut + deploy — tag main `vYYYY.MM.DD`, deploy it (pull/pin, venv, PATH links, cron) | `gazette version cut && gazette version deploy` | live |
| 08:05 | **the edition** — needs-you / anomalies / news / ambient, names the running version | `gazette notes --flare` | live |
| 07:19 | threads scan+weave (activity dashboard stays fresh) | `threads` | live |
| hourly | desk sync (new blocked items still flare immediately) | `desk sync` | live |
| —     | goal-portfolio pulse (weekly, not daily) | `/goal-review` | on demand |

Retired: the separate 08:35 desk→flare digest cron (folded into the
edition by arsenal PR #73); the nightly-only sweep and the delay-lane
veto window (2026-08-19 rework — versions are the rollback layer now).

## Response channel (next)

Reading needs a response as cheap as the read. Today: copy-paste the veto
command from the edition. Target (mailroom follow-up, arsenal issue): reply
in the Slack thread — "veto 141", "ship 37" — and mailroom applies the
label; optionally a 👍 react as a read-ack so edition-counting gets a real
"seen" signal instead of assuming delivery = read.
