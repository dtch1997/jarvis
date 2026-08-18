---
name: flare-proposal
description: "STUB — flare + desk BUILT 2026-08-16 (arsenal PRs #42/#46; jarvis #126 wired sanction/allowlist/crons); canonical docs = jarvis CLAUDE.md 'Attention routing' + arsenal packages; webhook still unconfigured (spool-only)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66a0be17-0b3d-4889-80d5-21fea170c689
  modified: 2026-08-17T08:19:33.583Z
---

Proposed 2026-08-11 (arsenal issue #36), BUILT 2026-08-16 via concierge task
t-0816-5bed. Canonical description now lives in jarvis CLAUDE.md ("Attention
routing — flare + desk") + `repos/arsenal/packages/{flare,desk}`; design
history in issue #36.

Operational:
- Shipped as TWO arsenal packages: `flare` (CLI+API, spool
  `~/.flare/log.jsonl`, 10-min spam guard, stdlib-only) and `desk`
  (waiting-on-Daniel inbox → `~/.desk/inbox.md`; `render|digest|sync|serve`;
  served via lobby /a/desk/). Wiring live: hourly `desk sync` + daily digest
  crons; CLAUDE.md sanction + BLOCKED-ON-DANIEL marker convention +
  allowlists (jarvis PR #126); HOUSE_RULES appended.
- Open polish issues: arsenal #43 (first-sync flood), #44 (marker
  doc-matches), #45 (stream consistency + rotation).
- ~~Slack push~~ LIVE 2026-08-18: Daniel's call — reuse the jarvis-mailroom
  Slack app instead of a webhook. flare gained a bot-token transport
  (chat.postMessage, arsenal PR #66; webhook still wins if ever configured;
  ok:false = failed send). Devbox config: `~/.config/flare/config.toml`
  [slack] bot_token+channel (0600). Pages land in #lab-notes-daniel
  (C0B5RUX4P26) — swap the channel id if #jarvis-flares is ever created
  (bot lacks channel-create scope). Verified end-to-end. Residual: pods
  spool-only until bellhop plumbs the two env vars — arsenal issue #67.

Related: [[arsenal-monorepo]], [[self-driving-jarvis]] (attention-routing
layer of the command-center build order), [[concierge-tool]].
