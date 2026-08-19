---
name: slack-post-style
description: "How the user wants Slack posts (paper critiques, lab notes) written — concise, TL;DR first"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 94bdcd57-54e7-4475-8b77-a0e74e00f3c8
  modified: 2026-08-18T06:15:41.638Z
---

For Slack posts (esp. paper critiques / lab notes): be concise, avoid word salad, and lead with a TL;DR of the subject (e.g. a one-line summary of the paper) before the analysis.

**Why:** the user found the verbose, multi-paragraph version harder to use than a tight version with a summary up top.

**How to apply:** open with a 1-2 sentence TL;DR of what's being reviewed; use short bullets; cut hedging/filler; put the actionable takeaway last. Applies to the [[amr-stronger-evidence-framework]] critique format too.

**Channel rule (2026-08-18):** ALL JARVIS-originated Slack messages go to
**#jarvis-dev (C0BQSU87ACD)** for now — never post to #lab-notes-daniel
(C0B5RUX4P26); that channel stays clean for Daniel's own captures (mailroom
still *reads* + ✅-reacts there). Enforced in ~/.config/flare/config.toml
(channel) and ~/.mailroom/config.toml (reply_on_route=false); applies equally
to ad-hoc MCP posts from sessions.

**Notification messages too (2026-08-18, mailroom/desk/flare rework):** any
agent-generated Slack notification (flares, desk sync, mailroom) follows the
same rule — a concise one-line headline, then **one bullet per point** (`•`),
never semicolon-joined run-on lines, never per-item message bursts, no
host/cwd boilerplate. Reference implementations: desk `sync()` batch flare and
mailroom's urgent batch flare (jarvis PRs #15/#16).
