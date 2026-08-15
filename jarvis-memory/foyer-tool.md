---
name: foyer-tool
description: "foyer — web front door for JARVIS tmux threads (sidebar + xterm terminal + plots/notes + plot roots + drag-reorder); arsenal PRs #14+#16 MERGED; STABLE URL via relay pod 5yhprobnt4loda; Daniel: already super useful"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0c90952c-f8ae-402a-939b-de4e79dbadf8
---

**foyer** (arsenal `packages/foyer`, PR #14 opened 2026-07-16): browser UI for
the tmux sessions agents live in. Left sidebar = every tmux session (agent dot
from `pane_current_command`, `pane_title` = Claude Code live status,
capture-pane preview); center = vendored xterm.js over a websocket→PTY bridge
spawning one `tmux attach` client per connection; right panel = Plots (newest
images ≤3 dirs under thread cwd) + Notes (`~/.foyer/notes/<session>.md`).

- `foyer serve` → **own** quick tunnel via `lobby.tunnel` — deliberately NOT
  behind the [[lobby-tool]] hub (its stdlib proxy buffers, no websockets, and
  the index is public while foyer is a shell). Lobby WS passthrough = possible
  follow-up.
- Auth: random token `~/.foyer/token` (?t= → cookie) on every route incl. WS;
  URL+token = shell access. Rotate by deleting the token file.
- PTY gotchas encoded: initial TIOCSWINSZ before spawn (0×0 renders nothing) +
  explicit `killpg(SIGWINCH)` on resize (PTY isn't the child's ctty). tmux
  sizes windows to smallest attached client — tiny ssh client letterboxes the
  browser.
- Tests: `FOYER_TMUX="tmux -L …"` private-socket e2e in package tests; CI
  matrix includes foyer.
- 2026-07-17 (2nd commit, Daniel's requests): per-thread **plot roots**
  (`~/.foyer/plotroots.json`, UI input, must be dir under $HOME — jarvis
  threads share cwd so default plots were identical) + **drag-to-reorder**
  sidebar (`~/.foyer/order.json`, manual order first, new sessions below by
  recency).
- 2026-07-17 WRAPPED: PR #14 + relay PR #16 both squash-merged, worktrees
  removed, `repos/foyer` symlink created. **Stable URL live**:
  `https://5yhprobnt4loda-8080.proxy.runpod.net` — relay pod `5yhprobnt4loda`
  (~$0.03/hr CPU, lobby.wiki provisioning pattern) runs `relay_httpd.py`, a
  stdlib byte pump (post-handshake WS = TCP, so terminal flows through);
  `foyer serve` publishes each fresh quick-tunnel URL to the relay's
  bearer-token control endpoint (`~/.foyer/relay.json`). Cookie sticks to the
  stable domain → token once per device. `foyer relay up|status|delete`.
  Live-verified: auth + sessions + terminal echo through the pod.
- 2026-07-17 PR #19 MERGED: **＋ new thread** (creates tmux session in
  configured workspace + types configured command; Daniel's
  `~/.foyer/config.json` = workspace ~/jarvis, command
  `claude --dangerously-skip-permissions` (flag added 2026-07-17 on request);
  send-keys so thread survives program exit) + **double-click rename** (migrates
  notes/plotroots/order keys). Gotcha fixed: pane-targeting tmux commands
  need `=name:` (trailing colon) on tmux 3.2a — bare `=name` = "can't find
  pane"; previews had been silently empty since v0.1. Test flake fix:
  per-test tmux sockets (shared socket races kill-server teardown).
- 2026-07-17 PR #20 MERGED: instant thread switching — per-thread kept-alive
  terminal+WS entries (LRU cap 8, pre-warm first 8 on load, 150ms stagger);
  measured: relay-chain WS handshake 705ms vs 5ms localhost, server attach
  ~10ms → cost is per-connection, so keep connections. Hidden slots =
  `visibility:hidden` NOT display:none (0-size client would letterbox tmux
  for all clients). Frontend-only changes go live on `git pull` — server
  serves static from main checkout per-request, no restart needed.
- 2026-07-17 PR #21 (kill threads: hover ✕ two-stage confirm; DELETE cleans
  plotroot+order, keeps notes) + PRs #22+#23 relay self-healing after a live
  outage. Root causes found: (1) relay target was in-memory only → pod/container
  restart = amnesia; (2) fresh trycloudflare subdomains have per-tunnel DNS
  records (NO wildcard) → pod resolver negatively caches NXDOMAIN → stable URL
  502s for minutes after each foyer restart (masqueraded as a crash). Fixes:
  serve keeper (60s ping, re-publish on missing/stale target_fp = sha256[:8]),
  crash-proof accept loop, gaierror→connect parent domain + TLS SNI routing,
  `foyer relay redeploy` (PATCH dockerStartCmd + restart = same pod id/URL).
  Gotcha: RunPod CPU pod container disk does NOT survive stop/start → disk
  persistence only helps same-container restarts; keeper is the real healer.
- Origin: Daniel wants a Silico-like app form factor for JARVIS threads
  (2026-07-16). Stage 2 idea (not built): chat-shaped rendering of session
  JSONL instead of raw terminal. Parked follow-up: systemd unit so
  foyer+tmux survive devbox reboot.

**session-dashboard skill deprecated 2026-07-16** (unused): moved to
`~/.claude/skills-archive/session-dashboard`, `~/.config/claude-dashboard`
removed. `session-rundown` kept.
