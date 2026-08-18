# Infrastructure-as-code audit (2026-08-18)

How much of JARVIS is versioned, what drifts, and what isn't versioned at all.
Input to the versioning plan (assigning version numbers to JARVIS). Audited
live on the devbox: home-dir layout, crontab, tool configs, spools, tmux,
`--check` drift gates.

## TL;DR

- The **core is genuinely IaC**: one monorepo (jarvis-os / jarvis-tools /
  jarvis-memory), crontab and PATH CLIs as build artifacts with `--check`
  drift gates, and a nightly deploy cron that makes `main` ≈ deployed within
  24h. Both drift checks pass today.
- The **soft edge is live config**: per-tool `config.toml`s are generated
  once, then hand-edited; committed defaults and live values drift in both
  directions (examples below).
- The **real gaps**: two crons execute unversioned code from `~/jarvis-data`
  (issue #17); the nightly memory-snapshot cron now auto-commits the *whole
  monorepo* to main (issue #2 comment); global `~/.claude` config, daemon
  topology (tmux), secrets inventory, and all SaaS-side state (Slack app,
  GitHub labels, RunPod, lobby tunnel) are unversioned.
- **Nothing carries a version number today**: zero git tags; only per-package
  semver in jarvis-tools (bellhop, ferry on PyPI); `changelog.md` is narrative
  and sporadic.

## Layer 1 — versioned and auto-deployed ✅

| What | Mechanism |
|---|---|
| CLAUDE.md, docs, goals/, wiki/, drafts/, ops/ | jarvis-os in the monorepo |
| All tool packages + `uv.lock` | jarvis-tools workspace |
| Memory stubs + MEMORY.md | jarvis-memory, nightly snapshot commit+push (03:41) |
| Session hooks, skills, settings | `jarvis-os/.claude/` (tracked) |
| Crontab | `ops/cron.tab` → `install-cron.sh`; `--check` **clean** today; two managed blocks (jarvis, life-theses) |
| PATH CLIs | `jarvis-tools/ops/link-clis.sh` (declared build artifact) |
| Deployment | 04:10 cron: `git pull` → `uv sync --all-packages` → `link-clis.sh` → `install-cron.sh` — continuous deploy from main |
| Project code | dedicated repos under `repos/` (pointers-not-code pattern) |

The deploy cron is the key property for versioning: **"deployed version" =
whatever main was at 04:10.** A release train only needs the cron to check out
a tag instead of main tip.

## Layer 2 — declared-as-code, drifts in practice ⚠️

Config-first knobs live in generated files that are then hand-edited; git only
has the (aging) defaults:

- `~/.config/desk/config.toml` — live corrected to `dtch1997/jarvis`, while
  the *committed* defaults still say `ArcadiaImpact/jarvis` + `dtch1997/arsenal`
  (stale since the cutover; a rebuild from code would watch the wrong repos).
- `~/.mailroom/config.toml` — generated with `backfill_days = 90`; the file
  wins over new code defaults, so the 21-day window change would silently not
  apply. (Live file fixed by hand 2026-08-18 — which is itself the pattern.)
- `~/concierge-home/config.yaml` — only `HOUSE_RULES.example.md` is versioned;
  the live config carries an incident-driven `default_backend` revert whose
  rationale exists only in comments in the unversioned file.
- `~/.config/flare/config.toml` — **contains the Slack bot token**, i.e. a
  secret living outside `~/.env`. It is also where the *destination channel*
  for all JARVIS Slack output lives: redirected live to `#jarvis-dev`
  (`C0BQSU87ACD`) on 2026-08-18 per Daniel (keep `#lab-notes-daniel` clean);
  `reply_on_route` paused in `~/.mailroom/config.toml` for the same reason.
  Both are live-only edits — a rebuild from git would silently resume posting
  to `#lab-notes-daniel`.
- Cron block header still says `ArcadiaImpact/jarvis`; entries path through
  the `~/jarvis` / `repos/arsenal` symlink chain (works, but
  `git -C repos/arsenal pull` now pulls the same monorepo a second time).

## Layer 3 — not versioned ❌

1. **Scheduled code outside git** — `~/jarvis-data/{runpod-availability/poll.py,
   pod-audit/audit.py,pod-audit/allowlist.json}` run from cron; `~/jarvis-data`
   is not a repo, and pod-audit's allowlist has a second hand-synced copy in
   `ops/pod-audit/`. → **issue #17**. Same class: `~/.habitat/backup.py` (03:17
   cron).
2. **Whole-monorepo auto-commit** — the 03:41 memory snapshot does
   `cd ~/jarvis-memory && git add -A`, which post-cutover stages the entire
   monorepo: nightly unreviewed direct-to-main commits of any dirty WIP,
   bypassing PR lanes (`main` HEAD is literally `auto-snapshot 2026-08-18`).
   → **commented on issue #2**.
3. **Global harness config** — `~/.claude/settings.json`, `statusline.sh`
   shim, plugins: unversioned (project-level `.claude/` is tracked; the global
   layer isn't).
4. **Secrets inventory** — `~/.env` (15 keys) is rightly out of git, but no
   committed `.env.example` names the required keys; rebuild = archaeology.
   Plus the flare bot token outside `~/.env` (above).
5. **Daemon topology** — concierge daemon, mailroom-dash, threads-dashboard,
   lobby hub live in hand-started tmux sessions; a reboot loses the execution
   layer with no boot script to restore it.
6. **SaaS-side state** — Slack app manifest (jarvis-mailroom scopes/channels),
   GitHub repo settings (lane labels, branch protection), Todoist project
   taxonomy, RunPod pods/volumes, GCS layout, lobby tunnel URL. Declared
   nowhere; recoverable only via docs/memory stubs.
7. **Spools** (fine as data, but note the durability asymmetry) — `~/.flare`,
   `~/.threads`, `~/.desk`, `~/.gazette`, `~/.mailroom` (the *thoughts spool is
   the durable copy* of captures — "retained provenance" — yet it's the one
   store with no git/GCS backup), `~/concierge-home/tasks+workspaces`.
8. **Legacy residue** — `~/jarvis-old`, `~/jarvis-memory-old`,
   `~/arsenal-old-clone` (holds the live `bellhop-nebius` worktree). Covered by
   issue #2's sweep bullet.

## Implications for version numbers

- **There is a natural release unit**: the monorepo. Everything that defines
  JARVIS behavior (CLAUDE.md, tools, crons, hooks, skills) is in one repo with
  one deploy path. Tag it (`v0.X.Y`), and make the 04:10 deploy cron check out
  the latest tag instead of main tip — versions then *gate* deployment instead
  of describing it after the fact, and the gazette lanes become the release
  pipeline.
- **Changelog**: `changelog.md` exists but is narrative and sporadic
  (last entry 2026-08-15). The gazette patch-notes stream is already the de
  facto changelog — a release tag could bundle the editions since the last tag.
- **Before v0.1 means anything**, close the gaps where deployed behavior isn't
  derivable from the repo: issue #17 (jarvis-data code), the memory-cron scope
  fix (issue #2), a `.env.example` + secrets-location convention, committed
  config snapshots (or `--check`-style drift gates) for the Layer-2 knobs, and
  a `ops/boot.sh` for the tmux daemon topology.

---
*Generated during the 2026-08-18 mailroom-noise session; drift checks
(`install-cron.sh --check`, config diffs) were run live, not inferred.*
