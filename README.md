# jarvis (monorepo)

Daniel's personal command center for high-throughput AI work, consolidated
into one monorepo. History-preserving migration (`git filter-repo
--to-subdirectory-filter` + unrelated-history merges); layout confirmed by
Daniel 2026-08-18.

## Layout

- **`jarvis-os/`** — the command center itself: CLAUDE.md conventions,
  goals/, wiki/, ops/ (crons), docs/, attention routing. Full history of
  what was `ArcadiaImpact/jarvis`.
- **`jarvis-memory/`** — the persistent agent memory (one file per fact +
  `MEMORY.md` index). Full history of `dtch1997/jarvis-memory`.
- **`jarvis-tools/`** — the utility monorepo (uv workspace,
  `packages/<tool>`: stagehand, bellhop, concierge, gazette, threads, flare,
  desk, …). Full history of what was `dtch1997/arsenal`.

Object-level projects stay in their own repos, cloned under
`jarvis-os/repos/` on the devbox (pointers, never code — see
`jarvis-os/README.md`, "the repos/ pattern").

## Migration status — ✅ CUT OVER (2026-08-18)

**This repo is live and authoritative.** The old repos
(`ArcadiaImpact/jarvis`, `dtch1997/jarvis-memory`, `dtch1997/arsenal`) are
archived read-only with pointer READMEs. Devbox layout: clone at
`~/jarvis-monorepo`; `~/jarvis` → `jarvis-os/`, `~/jarvis-memory` →
`jarvis-memory/`, `~/jarvis/repos/arsenal` → `jarvis-tools/` (symlinks, so
all pre-cutover paths keep resolving). Pre-cutover checkout preserved at
`~/jarvis-old` (worktrees repaired, remote archived); old arsenal clone at
`~/arsenal-old-clone`. Follow-ups tracked in issues.

### Cutover checklist

- [x] Final local layout confirmed (Daniel, 2026-08-18): `jarvis-os` /
      `jarvis-memory` / `jarvis-tools`
- [x] Cutover timing confirmed (Daniel, 2026-08-18 — dinner window) (a quiet window — the
      re-sync + repoint below is ~an hour of downtime for crons/agents)
- [x] Quiesce + merge or re-target open PRs on all three old remotes
      (gazette sweep helps: let the lanes drain; `lane:blocked` items like
      arsenal#37 move or close explicitly)
- [x] Final re-sync: re-run the filter-repo import so no commits land in
      the old remotes after the snapshot
- [x] Repoint the devbox: clone monorepo once; symlink `~/jarvis` →
      `<clone>/jarvis-os`, `~/jarvis-memory` → `<clone>/jarvis-memory`,
      and keep `~/jarvis/repos/arsenal` resolving to `<clone>/jarvis-tools`
      so cron paths, hooks, HOUSE_RULES, and the arsenal `.venv` path in
      `ops/cron.tab` survive unchanged
- [x] Re-run `uv sync --all-packages` in jarvis-tools; re-run
      `ops/link-clis.sh`; verify `ops/install-cron.sh --check` passes and a
      `desk sync` / `flare` / `gazette status` round-trip works from the
      new paths
- [x] Consumer-mode plumbing: create the `lane:*` + `veto` labels on
      `dtch1997/jarvis`; update gazette + desk configs
      (`~/.config/gazette/config.toml`, `~/.config/desk/config.toml`) from
      the two old repos to the monorepo; note per-directory lane routing
      inside one repo (jarvis-tools changes = `lane:delay`) now relies on
      the protected-path demotions — extend `protected_globs` with
      `jarvis-tools/packages/**` if label discipline slips
- [x] jarvis-tools specifics: PyPI releases (bellhop, ferry-sync) keep
      working from the subdirectory (update any release scripts/URLs);
      `pyproject.toml` git-URL deps pointing at
      `github.com/dtch1997/arsenal#subdirectory=packages/<tool>` must be
      repointed at the monorepo path
- [x] Archive `ArcadiaImpact/jarvis`, `dtch1997/jarvis-memory`, and
      `dtch1997/arsenal` with pointer READMEs to this repo
