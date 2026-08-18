---
name: statusline-tool
description: Claude Code status line captured as arsenal packages/statusline; ~/.claude/statusline.sh is now a thin shim into the arsenal venv
metadata: 
  node_type: memory
  type: reference
  originSessionId: 051ec893-3964-46f3-9fbb-6aded536a024
  modified: 2026-08-18T00:39:39.298Z
---

Claude Code's status line (model / context bar / cost) is rendered by
`claude-statusline` from [[arsenal-monorepo]] `packages/statusline`
(PR #62, merged 2026-08-18) — a faithful Python port of the old
unversioned `~/.claude/statusline.sh` bash script.

Wiring: `~/.claude/settings.json` `statusLine.command` → `bash
~/.claude/statusline.sh`, which is now a thin shim that `exec`s
`~/jarvis/repos/arsenal/.venv/bin/claude-statusline` (fallback:
`~/.claude/statusline.sh.pre-arsenal.bak`, the original script).

Session segments (arsenal PR #63, jarvis PR #142, 2026-08-18): the line
also shows a dim **topic** (harness auto `session_name`, override with
`claude-statusline note "..."`) and bold-red **wrap-up flags** —
`claude-statusline flag "open PR" / unflag <substr> / show`, keyed on
`$CLAUDE_CODE_SESSION_ID`, sidecar in
`~/.claude/statusline/sessions/<id>.json` (30-day prune). Cast as an
explicit top-level-session capability in jarvis CLAUDE.md attention
routing (jarvis PR #147): note on pivot, flag obligations as they
accrue, unflag/drain at wrap-up (now SOP wrap-up step 4, jarvis PR
#149). On PATH like all agent-facing arsenal CLIs —
`repos/arsenal/ops/link-clis.sh` owns the `~/.local/bin` symlinks
(arsenal PR #69; `--check` for drift; old pip wrappers preserved as
`*.pre-arsenal`).

Multi-line (arsenal PR #64): Claude Code renders every printed line as
its own status row, so the layout is stacked — vitals (context-tinted) /
topic (dim) / flags (bold red), empty rows dropped. To extend: add a
segment function to a row in the `LINES` list in
`packages/statusline/src/statusline/render.py` (segments self-style),
then `uv sync --all-packages` at the arsenal root. Tests:
`uv run pytest packages/statusline/tests`.

Statusline payload gotcha/goldmine: the harness stdin JSON also carries
`workspace` (cwd/project/repo), `rate_limits` (5h/7d used %), `cost`
line counts, `fast_mode`, `exceeds_200k_tokens` — all unused so far.
