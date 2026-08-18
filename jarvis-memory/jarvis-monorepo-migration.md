---
name: jarvis-monorepo-migration
description: "dtch1997/jarvis private monorepo (jarvis-core + jarvis-memory, histories preserved) created 2026-08-17; snapshot only, cutover pending Daniel"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbead54c-64d5-4268-bdc2-2bd5b820f1b5
  modified: 2026-08-18T00:40:21.377Z
---

Daniel decided (2026-08-17) that JARVIS is his creation, not Arcadia's, and
wants it in a personal monorepo. **https://github.com/dtch1997/jarvis
(PRIVATE)**; snapshot refreshed 2026-08-18 to Daniel's confirmed layout:

- `jarvis-os/` = full history of ArcadiaImpact/jarvis (filter-repo
  `--to-subdirectory-filter`, renamed from the earlier `jarvis-core`)
- `jarvis-memory/` = full history of dtch1997/jarvis-memory (branch `master`)
- `jarvis-tools/` = full history of dtch1997/arsenal (added 2026-08-18)

All merged with `--allow-unrelated-histories`; commit counts verified
(389 source + merges). Re-syncing is cheap — re-run the import (recipe:
clone each source, filter-repo to subdir, merge into fresh repo,
force-push); never hand-merge.

**Status: snapshot only — NOT cut over.** Authoritative live sources remain
ArcadiaImpact/jarvis (`~/jarvis`), dtch1997/jarvis-memory (`~/jarvis-memory`),
and dtch1997/arsenal (`~/jarvis/repos/arsenal`). Full cutover checklist in
the monorepo root README — incl. gazette/desk config repoint + lane labels
on the new repo, arsenal git-URL deps
(`#subdirectory=packages/<tool>`) repoint, PyPI release paths, symlink
strategy so devbox paths survive.

BLOCKED-ON-DANIEL: confirm cutover timing (layout was confirmed 2026-08-18;
the re-sync + repoint is ~an hour of cron/agent downtime).

Related: [[self-driving-jarvis]], [[arsenal-monorepo]].
