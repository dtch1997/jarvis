---
name: flare-proposal
description: "flare BUILT 2026-08-16 (arsenal PR #42 + #46) — universal push channel + desk waiting-on-Daniel inbox; webhook still unconfigured (spool-only)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66a0be17-0b3d-4889-80d5-21fea170c689
  modified: 2026-08-11T14:45:57.759Z
---

**flare** — proposed 2026-08-11 as [[arsenal-monorepo]] issue #36 (https://github.com/dtch1997/arsenal/issues/36). Not yet built.

One universal, push-based, always-allowed channel any agent (session, concierge worker, arch2 fleet, pod script) can use to page Daniel. Inspired by a field report about a `distress_call` tool (AI welfare + opsec).

MVP design (converged in-session):
- `packages/flare`: CLI `flare "msg" --sev warn` + `flare.send()`; Slack incoming webhook → `#jarvis-flares`; config `~/.config/flare/config.toml`; stdlib/httpx only (uvx-able on bare pods)
- Auto-stamped context: host, cwd, branch, `CLAUDE_SESSION_ID`, concierge task id (first line → reply via `pool.msg <tid>` from phone)
- Local `~/.flare/log.jsonl`; 10-min same-message spam guard
- Crux = companion changes outside arsenal: `Bash(flare *)` allowlist (jarvis + concierge workers' settings) + sanction paragraph in CLAUDE.md / HOUSE_RULES.md ("use any time, any reason, low bar")
- Acceptance: headless `claude -p` worker → `flare "test"` → phone, no permission prompt
- Cut from v1: foyer links (phase-2 highest value), two-way replies, real threading

**BUILT 2026-08-16** via concierge task t-0816-5bed → arsenal PR #42 (merged)
+ #46 (desk self-notification loop fix). Shipped as TWO packages: `flare`
(CLI+API, spool ~/.flare/log.jsonl, 10-min spam guard, stdlib-only) and
`desk` (waiting-on-Daniel inbox: concierge blocked/failed + PR ages +
BLOCKED-ON-DANIEL markers + recent flares → ~/.desk/inbox.md; sync flares
new items). Wiring live: hourly `desk sync` + daily digest crons; CLAUDE.md
sanction + marker convention + allowlist (jarvis PR #126); HOUSE_RULES
appended live; served via lobby /a/desk/. First sync surfaced 9 blocked/
failed pool tasks (oldest 38d). Polish issues: arsenal #43 (first-sync
flood), #44 (marker doc-matches), #45 (stream consistency + rotation).
BLOCKED-ON-DANIEL: drop a Slack incoming-webhook URL for #jarvis-flares into
~/.config/flare/config.toml ([slack] webhook_url) to turn on phone push.
