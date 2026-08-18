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
   comes first. Merges the veto-window items and desk items into one list,
   each with its **default outcome** stated ("merges at tonight's sweep
   unless vetoed" vs "sits until you act") and a copy-pasteable veto
   command. The `desk digest` is folded in here — no separate 08:35 flare.
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

## Veto windows count delivered editions

A `lane:delay` PR merges only after it has **appeared in 2 morning
editions** (`delay_editions`), not after 36 wall-clock hours. Each
`gazette notes` run logs which PRs it showed (`~/.gazette/editions.jsonl`);
a skipped morning — weekend, dead cron — pauses the window instead of
letting conventions merge unseen. `delay_hours` survives only as a stall
detector: a PR aged 3× the window with too few editions raises an anomaly
("is the notes cron running?").

## Components

| when  | what | tool | status |
| ----- | ---- | ---- | ------ |
| 03:29 | nightly PR merge sweep (produces the morning's news) | `gazette sweep` | live |
| 04:10 | deploy — pull merged main, refresh venv/PATH links, reconcile cron | `ops/cron.tab` deploy entry | this PR |
| 08:05 | **the edition** — needs-you / anomalies / news / ambient | `gazette notes --flare` | arsenal PR #73 |
| 07:19 | threads scan+weave (activity dashboard stays fresh) | `threads` | live |
| hourly | desk sync (new blocked items still flare immediately) | `desk sync` | live |
| —     | goal-portfolio pulse (weekly, not daily) | `/goal-review` | on demand |

Retired: the separate 08:35 desk→flare digest cron (folded into the
edition by arsenal PR #73; removed from `ops/cron.tab` in this PR).

## Response channel (next)

Reading needs a response as cheap as the read. Today: copy-paste the veto
command from the edition. Target (mailroom follow-up, arsenal issue): reply
in the Slack thread — "veto 141", "ship 37" — and mailroom applies the
label; optionally a 👍 react as a read-ack so edition-counting gets a real
"seen" signal instead of assuming delivery = read.
