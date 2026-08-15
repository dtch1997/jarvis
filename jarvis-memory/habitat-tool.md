---
name: habitat-tool
description: "habitat — personal habit tracker web app on a long-lived RunPod CPU pod; arsenal package, celebration-first design, backup-based persistence"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5ff2b1b6-be30-418f-8b17-025747a37f12
---

**habitat** — Daniel's personal habit tracker, built 2026-07-11 (arsenal PR #3,
branch `habitat`). In [[arsenal-monorepo]] at `packages/habitat`.

- **Live**: `https://ee307drqzcwgwr-8080.proxy.runpod.net` (pod `habitat`, id
  `ee307drqzcwgwr`, 1 vCPU SECURE ~$0.03/hr, always-on). Secret + pod info in
  `~/.habitat/config.json`. Seeded with the 10 Todoist Habits-project habits;
  Todoist itself deliberately untouched (Daniel keeps 1–2 daily intentionality
  reminders there; habitat is the "good to do once in a while" tier).
- **Design intent**: celebration-first — recency, monthly counts, heatmap,
  legacy_count head-starts from the Todoist era; NO daily-streak guilt. Keep
  this framing when extending it.
- **Architecture**: [[lobby-tool]] wiki pattern extended — stdlib-only
  `server.py` + SPA pushed as tarball to token-gated `/api/code`; tiny
  `bootstrap.py` in dockerStartCmd supervises (server exits 42 to restart
  after self-update). `habitat provision|deploy|status|backup|restore|seed`.
- **Persistence gotcha**: RunPod CPU pods have NO durable disk — the pod's
  SQLite is the live copy only. Nightly devbox cron (03:17,
  `~/.habitat/backup.py`, repo-independent) mirrors to `~/.habitat/backups/`.
  After a pod rebuild/restart the DB is empty: run `habitat provision &&
  habitat restore`.
- Todoist API cannot recover per-day recurring-task completion history — only
  `completed_count` totals (carried as `legacy_count`).
- Headless-browser trick used for UI checks on this box: playwright chromium
  + `apt-get download libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0` extracted
  via `dpkg -x` + `LD_LIBRARY_PATH` (no root needed).
