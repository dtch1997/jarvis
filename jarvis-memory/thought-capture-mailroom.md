---
name: thought-capture-mailroom
description: "mailroom (arsenal, planned) — drain Daniel's capture surfaces (Todoist Inbox, voice memos, Slack #lab-notes-daniel) onto existing spines; spec PR #138"
metadata: 
  node_type: memory
  type: project
  originSessionId: df174149-3fb4-473a-8cf9-d6e768706786
  modified: 2026-08-18T01:57:34.774Z
---

Thought-capture ingestion pipeline, Daniel's ask 2026-08-17: his three
capture surfaces (Todoist, voice memos, Slack lab-notes) should be tracked
and acted on by jarvis. Design = the inbound mirror of [[threads-tool]]:
ingest → haiku triage → route onto existing spines (threads notes, Todoist
projects, goals/, papers, flare), loop-closure marks at each source, daily
digest as veto surface, no second registry. Spec:
`docs/thought-capture.md` — **jarvis PR #138 OPEN** (also adds a
command-center.md pointer). Working name `mailroom` (Daniel may rename, cf.
loom→threads).

Standing decisions (Daniel, 2026-08-17):
- Separate from threads for now; future convergence = one PKM/Obsidian-style
  vault (threads already mirrors to `~/.threads/vault/`).
- **Todoist is capture-only; drain to zero — but FILE, NEVER COMPLETE**
  (Daniel's explicit concern 2026-08-17: no checking off things that
  didn't get done). Task-typed items are *moved* Inbox→project and stay
  open; close-with-comment only for non-task captures transferred to a
  liveness-tracked spine (threads note, goal bullet, new Papers-to-read
  task); unsure → treat as task. Stale sweep of curated projects is
  propose-only.
- **Voice memos**: query → NVIDIA Parakeet transcription (no GPU on devbox
  → CPU, bellhop for backfill) → raw audio to GCS as provenance.
  Recommended transport: iOS Shortcut → Drive folder → rclone pull.
- **Slack**: multi-channel by config; MVP = `#lab-notes-daniel` only.
- Auto-dispatch of concierge tasks from thoughts = propose-only rung.

Setup needed (none of the claude.ai MCPs work headless/cron; `~/.env` has
no Slack/Todoist creds today):
- ~~Slack app token~~ DONE 2026-08-17: app `jarvis-mailroom` (bot
  `U0BQWRJETGR`, Arcadia workspace), `SLACK_MAILROOM_TOKEN` +
  `SLACK_MAILROOM_APP_TOKEN` in `~/.env`, auth.test verified. NB Daniel
  pasted tokens in-session knowingly (they appear in transcripts).
  Bot invited to **#lab-notes-daniel = C0B5RUX4P26** (private) 2026-08-17;
  history read + reactions.add (✅) verified end-to-end. 2026-08-18: flare now
  rides this same app (bot-token transport, arsenal #66 → #lab-notes-daniel)
  — see [[flare-proposal]].
- ~~Todoist API token~~ DONE 2026-08-18: `TODOIST_API_TOKEN` in `~/.env`,
  verified. **Gotcha: REST v2 (`/rest/v2/`) is HTTP 410 GONE — use the
  unified API `https://api.todoist.com/api/v1/` (cursor-paginated
  `{results, next_cursor}` envelopes).** Inbox project id
  `6RJ8MCM4gr9C9WpJ`; drain baseline 2026-08-18 = 52 open Inbox tasks
  (30 older than 30d).
- ~~voice leg~~ DONE 2026-08-18 via **Slack transport** (Daniel's pick):
  record clips in #lab-notes-daniel (or share Voice Memos into it); bot
  scope `files:read` added; end-to-end hand-verified — real clip →
  bot-token download → ffmpeg 16kHz mono → **Parakeet via
  `onnx-asr[cpu,hub]`** (no NeMo; ~8s model load, sub-realtime on CPU,
  this box has no GPU) → transcript. Drive/rclone demoted to upgrade path
  (claude.ai Drive connector = dtch009@gmail.com, interactive-only,
  unusable from cron). ~~Original Drive plan~~: iOS Shortcut + `rclone config` for a
  `drive:` remote (only `gcs:` exists)

Spec MERGED: PR #138 (854f7d2) + voice-amendment PR #148 — both now live
in the **monorepo** (dtch1997/jarvis, cutover 2026-08-18 01:10; spec =
`jarvis-os/docs/thought-capture.md`, package target =
`jarvis-tools/packages/mailroom`). All three legs credentialed +
hand-verified (74s real Voice Memo transcribed cleanly; a real capture —
seeded threads note `spar-mentoring-model`). Build dispatch: ~~t-0818-bf5d~~ FAILED $0 — pool `default_backend` is now
**codex** (line-worker, can't do build tasks; always pass
`backend="claude"` for delegation-class work). **Redispatched
t-0818-f5e2** (backend=claude, $30/6h; attempt 1 spent $12 building the
package (commit on pool/t-0818-f5e2) + Slack backfill (~307 thoughts
spooled to ~/.mailroom) but FAILED on the known park-and-exit strike
pattern (concierge stub lesson 3 — worker "stood by" instead of
signal_waiting; attempt-kill also killed its ingest; Todoist untouched,
still 52). REQUEUED via file-edit 2026-08-18 ~02:00 w/ SUPERVISOR_NOTE.md
+ max_attempts 6 → **GATE-PASSED, done**), gate
`PrOpen() & ShellOk(". ~/.env; cd jarvis-tools && .venv/bin/mailroom
ingest --check && route --check")`; hard rules in spec: Todoist
file-never-complete, no writes outside C0B5RUX4P26, no threaded replies
on backfill. **BUILD DONE 2026-08-18 03:1x → monorepo PR #15 OPEN** (+2966, 38 tests;
live-fire: 458 thoughts — slack 404 / voice 2 / todoist 52; 95% auto-routed,
406 ✅ reactions, both clips through Parakeet; Todoist drain 52 → 6
`mailroom-unclear` (all X-link captures) via 32 moves + 14 transfer-closes,
**0 task-completions** — verified via API, not just self-report; dashboard
live /a/mailroom/, tmux mailroom-dash). Worker also fixed a dead-code
`SlackClient.download` bug. Post-merge steps: run `ops/install-cron.sh`
(2-hourly ingest+route, daily digest crons in this PR).

**Noise fixes 2026-08-18** (Daniel: "ok it's officially too much lol" after the
2026-08-17 double-burst — 12 per-item capture flares at 20:07, echoed verbatim
by hourly `desk sync` at 21:07): capture window 90d → **21d** (Slack backfill +
Todoist Inbox pull, honored by `ingest --check`); urgent captures now batch
into **one flare per route run** (stale >7d / backfill thoughts never flare);
triage urgency bar tightened (high = harm if delayed ~48h; important ≠ urgent).
Pushed onto PR #15 branch. Companion **jarvis PR #16 (lane:delay)**: desk sync
batch-flares (one summary, not per item), desk stops re-flaring
source=mailroom, 150-char item-title cap, flare Slack rendering drops host/cwd
boilerplate. Dup mailroom build PR #13 closed (branch pool/t-0818-bf5d kept).
