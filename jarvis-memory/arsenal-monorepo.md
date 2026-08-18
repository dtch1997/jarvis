---
name: arsenal-monorepo
description: "the tools workspace: monorepo-root uv workspace (dtch1997/jarvis) — generic tools in jarvis-tools/packages/, policy tools (gazette/desk/threads) in jarvis-os/packages/ since PR #11; venv at monorepo root; new tools born as workspace packages, not repos"
metadata: 
  node_type: memory
  type: project
  originSessionId: 74110705-dbff-4bfa-9e57-b7cbe3af3921
  modified: 2026-08-18T00:39:48.159Z
---

**arsenal → jarvis-tools** — since the 2026-08-18 monorepo cutover this
lives at `jarvis-tools/` in dtch1997/jarvis (`repos/arsenal` is a symlink).
Shape: **uv virtual workspace whose root is the MONOREPO root** (since the
os/tools boundary move, monorepo PR #11): `[tool.uv.workspace] members =
["jarvis-tools/packages/*", "jarvis-os/packages/*"]`, one root `.venv` at
`~/jarvis-monorepo/.venv` via `uv sync --all-packages`. Generic standalone
tools live in `jarvis-tools/packages/`; **policy tools (gazette, desk,
threads — code that co-evolves with CLAUDE.md) live in
`jarvis-os/packages/`**; dependency direction os → tools only. Each package
keeps its own name/version/CLI/import path (no `arsenal.` namespace). CI =
pytest matrix in root `.github/workflows/ci.yml` over both roots (update
per new package).

- Cross-package deps: `[project] dependencies` use the arsenal
  **subdirectory git URL** (`lobby @ git+https://github.com/dtch1997/arsenal#subdirectory=packages/lobby`,
  works with plain pip anywhere — verified externally incl. transitive
  resolution), overridden locally by `[tool.uv.sources] <name> =
  { workspace = true }`.
- Histories preserved: each repo was `git filter-repo
  --to-subdirectory-filter packages/<name>` then merged
  `--allow-unrelated-histories`, so `git log packages/<name>` reaches the
  original first commits (authoring dates intact).
- **Wave 1 DONE (2026-07-10):** [[lobby-tool]], [[ferry-tool]], databrowser.
  Old repos dtch1997/{lobby,ferry,databrowser} ARCHIVED with pointer notes;
  local `repos/{lobby,ferry,databrowser}` are now **symlinks** into
  `repos/arsenal/packages/` so old paths keep working. Lobby hub + tool
  registrations now run from the arsenal venv.
- **Waves 2+3 DONE (2026-07-10):** stagehand, cowrite, cairn, reportly,
  bellhop, concierge all in (310 tests green across the workspace). Concierge
  daemon NOT restarted — its editable install resolves through the
  repos/concierge symlink with identical content, so the two `waiting` tasks
  were untouched. Stale stagehand PR #24 closed at archive time. jarvis
  CLAUDE.md updated (PR #106): arsenal = tooling home, serving via lobby hub.
- Excluded by choice: cherami (personal), diffscope (research artifact),
  open-tinker (ArcadiaImpact infra).
- **Convention going forward:** new utilities are born as workspace
  packages, not standalone repos — `jarvis-tools/packages/<name>` if generic,
  `jarvis-os/packages/<name>` if they implement jarvis policy.
- **CLIs on PATH (2026-08-18, arsenal PR #69):** `ops/link-clis.sh` owns
  `~/.local/bin` symlinks for every agent-facing CLI (flare, desk, threads,
  claude-statusline, lobby, ferry, cowrite, cairn, reportly, gazette,
  arxivist, foyer, bellhop, databrowser) → the workspace venv. Call them
  bare; `--check` diffs for drift; add new CLIs to the script's list.
  Pre-existing pip-era wrappers (lobby/cowrite pointed at FROZEN copies in
  `~/.local/lib/python3.10/site-packages`) moved aside as `*.pre-arsenal`.
- **VENV GOTCHA (2026-07-16, bit for real):** the root `.venv` must stay in
  `uv sync --all-packages` state — a plain `uv run <cmd>` at the arsenal root
  re-syncs to root-only deps and can prune/corrupt package-extra deps. It
  left `httpx-sse` with dist-info but NO module dir (uv then thinks it's
  installed; `--reinstall-package httpx-sse` fixed it), which crashed
  **concierge worker spawns** (`claude_agent_sdk → mcp → httpx_sse` import) —
  3 attempts burned in seconds, task marked failed, no session ever started.
  Symptom signature: attempts with `session_id: null` + `cost_usd: null`
  dying <5s apart → read `logs/<tid>/attempt-*/agent.err` first. Prefer
  `.venv/bin/python` for ad-hoc scripts at the arsenal root; if venv state is
  suspect, `uv sync --all-packages` (+ `--reinstall-package <pkg>` for
  dist-info-only ghosts).
