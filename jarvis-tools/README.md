# jarvis-tools

The generic-tools half of the workspace: every research-infrastructure
tool that is a **standalone, reusable library** — one package per tool,
one lockfile, one venv (historically the "arsenal" repo). Each tool keeps
its own package identity (name, version, CLI, import path) —
`packages/<tool>/` is a normal installable package; the workspace just
makes them develop and refactor together.

**The boundary rule:** a package belongs here only if it is a *dumb
mechanism* — any jarvis-specific meaning lives in CLAUDE.md or a config
file, never in the code. Tools whose code implements jarvis operating
policy and must co-evolve with the agent contract (`gazette`, `desk`,
`threads`) live in [`../jarvis-os/packages/`](../jarvis-os/packages/)
instead — same workspace, same venv, different contract. Dependency
direction: jarvis-os packages may depend on jarvis-tools packages, never
the reverse.

| Package | What it is |
|---|---|
| [`stagehand`](packages/stagehand) | declarative DAG engine for orchestrating steps at scale, with live monitoring |
| [`bellhop`](packages/bellhop) | ephemeral RunPod/Modal compute: check code in, run, bring results back (PyPI: `bellhop-py`) |
| [`concierge`](packages/concierge) | worker pool over headless Claude sessions: durable tasks in, gated artifacts out |
| [`flare`](packages/flare) | universal push-based distress channel (webhook + spool, stdlib-only) |
| [`lobby`](packages/lobby) | one tunnel for all local apps: hub daemon + index + `/a/<name>/` reverse proxy + pluggable tunnel providers (`lobby.tunnel`) |
| [`ferry`](packages/ferry) | bytes ↔ GCS: `push`/`pull`/`Remote` by path (rclone) + `ferry.cas` content-addressed store (PyPI: `ferry-sync`) |
| [`databrowser`](packages/databrowser) | JSONL → static HTML browser, served through the lobby hub |
| [`cowrite`](packages/cowrite) | co-write Markdown drafts with an AI in the browser |
| [`curator`](packages/curator) | claims-and-figures ledger: capture plots with provenance at creation time, curate claims in a browser gallery, export a write-up skeleton |
| [`reportly`](packages/reportly) | experiment-report standard: scaffold, lint, build |
| [`arxivist`](packages/arxivist) | arXiv papers → structured, agent-legible markdown (native-HTML-first parse, PDF fallback, outline/section CLI) |
| [`foyer`](packages/foyer) | web front door for the tmux sessions your agents live in: session sidebar + live terminal (websocket PTY bridge) + plots/notes panes, own tunnel via `lobby.tunnel` |
| [`statusline`](packages/statusline) | Claude Code status line renderer (`claude-statusline`): harness stdin JSON → colored model/context-bar/cost line; extend by adding segments |
| [`cairn`](packages/cairn) | minimal, git-friendly dependency-aware issue graph for coding agents |
| [`podcaster`](packages/podcaster) | topic → listenable podcast episode: web-researched brief, style-gated spoken-word script, narrated MP3 (Piper on CPU) |

## Use

The uv workspace root is the **monorepo root** (one level up), so the
shared venv is `../.venv`:

```bash
cd .. && uv sync --all-packages    # one venv, every tool editable, every CLI
jarvis-tools/ops/link-clis.sh      # symlink agent-facing CLIs into ~/.local/bin
uv run pytest jarvis-tools/packages/lobby/tests
```

`ops/link-clis.sh` owns the `~/.local/bin` symlinks (PATH links are a build
artifact): every CLI in its list resolves bare from any shell, always to the
workspace venv. `--check` diffs live-vs-repo; after adding a CLI to a
package, add it to the list, merge, re-run.

Install a single tool anywhere (plain pip works):

```bash
pip install "git+https://github.com/dtch1997/jarvis#subdirectory=jarvis-tools/packages/lobby"
```

Cross-package dependencies are declared as those subdirectory URLs, with
`[tool.uv.sources] <name> = { workspace = true }` overriding to the local
editable inside the workspace.

## Conventions

- One tool = one directory under `packages/`, with its own `pyproject.toml`,
  `src/` (or flat) layout, and `tests/`.
- Tools stay import-compatible with their pre-monorepo selves — no
  `arsenal.` namespace.
- Zero-dep cores, lazy heavy imports behind extras (`ferry-sync[gcs]`).
- CI runs each package's tests separately (matrix in
  `.github/workflows/ci.yml` at the repo root).
- Histories were preserved on merge (`git filter-repo
  --to-subdirectory-filter`), so `git log packages/<tool>` goes back to
  each tool's first commit.
