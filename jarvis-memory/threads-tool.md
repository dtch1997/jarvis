---
name: threads-tool
description: threads (arsenal) — bottom-up activity spine; session→summary→thread weave; scan needs ANTHROPIC_API_KEY sourced
metadata: 
  node_type: memory
  type: reference
  originSessionId: 80a4fda1-cc56-497e-9354-b4aac2647dd7
  modified: 2026-08-17T23:39:01.571Z
---

`threads` (arsenal `packages/threads`): scans `~/.claude/projects` transcripts
into `~/.threads/summaries/`, weaves them onto memory-registry slugs
(a thread = a stub in `~/jarvis-memory`; see [[bottom-up-direction-philosophy]]).
Commands: `scan` / `weave` / `render` / `status` / `serve` (lobby hub). To put a
session on a thread deliberately: edit/create the stub *during the session* —
weave's `stub-edit` pass assigns it at 0.95 confidence.

**Gotcha (2026-08-17):** `threads scan` shells out to `claude -p --bare` with
`CLAUDE_CONFIG_DIR=/tmp/threads-claude` (isolated, so its own transcripts don't
pollute the corpus) — that dir has no OAuth creds, so auth comes only from
ambient `ANTHROPIC_API_KEY`. Non-login shells (Claude Code Bash tool, cron)
must `set -a; . ~/.env; set +a` first or every summarize call fails with
"Not logged in" (non-fatal: scan reports 0 summarized). Filed as arsenal
issue #58 (fail loudly + doc fix). No cron installed by design; if one is
added to `ops/cron.tab` it must source `~/.env`.

Binary: `repos/arsenal/.venv/bin/threads` (not on default PATH in tool shells).
