---
name: jarvis-monorepo-migration
description: "CUT OVER 2026-08-18: dtch1997/jarvis monorepo (jarvis-os + jarvis-memory + jarvis-tools) is live+authoritative; old repos archived; devbox on symlinks"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbead54c-64d5-4268-bdc2-2bd5b820f1b5
  modified: 2026-08-18T06:16:14.527Z
---

**CUT OVER 2026-08-18 (dinner window, Daniel-approved).**
**https://github.com/dtch1997/jarvis (PRIVATE) is live and authoritative**:
`jarvis-os/` (ex ArcadiaImpact/jarvis) + `jarvis-memory/` (ex
dtch1997/jarvis-memory) + `jarvis-tools/` (ex dtch1997/arsenal), full
histories preserved via filter-repo.

- **Old repos ARCHIVED** (read-only, pointer READMEs): ArcadiaImpact/jarvis,
  dtch1997/arsenal, dtch1997/jarvis-memory. All open PRs were drained first
  (merged #141/#148/#150/#151, arsenal #73; arsenal #37 closed → monorepo
  issue #1, blocked on Nebius creds).
- **Devbox layout**: clone at `~/jarvis-monorepo`; symlinks `~/jarvis` →
  `jarvis-os/`, `~/jarvis-memory` → `jarvis-memory/`,
  `~/jarvis/repos/arsenal` → `../../jarvis-tools`. All pre-cutover absolute
  paths (crons, hooks, venv shebangs, HOUSE_RULES) resolve unchanged.
  jarvis-tools has a fresh `.venv` (uv sync --all-packages), CLIs relinked.
- **Verified post-cutover**: install-cron --check green; gazette status
  (watches dtch1997/jarvis, lane labels created); desk digest; threads
  status 97% match; cowrite page 200; flare→Slack round-trip.
- **Leftovers**: pre-cutover checkouts at `~/jarvis-old` and
  `~/arsenal-old-clone` (worktrees repaired, remotes archived) — delete
  once their sessions finish. Follow-ups in **monorepo issue #2**: repoint
  jarvis-tools git-URL deps, PyPI release paths, CLAUDE.md
  monorepo-awareness (git in ~/jarvis now operates on the whole monorepo;
  gitignore anchoring), stale-worktree sweep, desk/lobby restart
  (jarvis-b5).
- **Gotcha**: `git worktree` operations from `~/jarvis` now create
  monorepo-rooted worktrees/branches; patch notes only see monorepo merges
  from now on (pre-cutover history stays in the archived repos).
- **os/tools boundary (2026-08-18, PR #11, lane:delay)**: policy tools
  (gazette, desk, threads — code that co-evolves with CLAUDE.md) moved to
  `jarvis-os/packages/`; jarvis-tools keeps only generic mechanisms. uv
  workspace root lifted to the **monorepo root** (venv = `<root>/.venv`;
  link-clis + cron.tab repointed). Dependency rule: os → tools, never
  reverse. Also revived CI (workflows were DEAD since cutover —
  `jarvis-tools/.github/` is ignored by GitHub; now at root `.github/`).
  Both repo secrets set from ~/.env, Daniel-approved 2026-08-18
  (`RUNPOD_API_KEY` + bellhop-live weekly schedule restored;
  `PYPI_TOKEN` → tag-publish path unblocked). Post-merge cleanup: `rm -rf
  jarvis-tools/.venv` (stale old-root venv).

Related: [[self-driving-jarvis]], [[arsenal-monorepo]].
