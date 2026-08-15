---
name: cairn-tool
description: "minimal stdlib-only dependency-aware issue graph for agents (file-per-issue, ready-queue, agent memory); in-house lightweight alternative to Beads"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3e6b72c3-9a02-4064-86d3-02d03acfd830
---

`cairn` — a minimal, stdlib-only (zero runtime deps) dependency-aware issue
graph for coding agents; the in-house lightweight alternative to Beads
(`bd`) built after a security review flagged Beads' default-on telemetry to
`gastownhall-eventsapi.com` (which its own SECURITY.md falsely denies) + heavy
Dolt/cgo footprint.

Core design: **one JSON file per issue** at `.cairn/issues/<id>.json` so
concurrent agents/branches merge cleanly with no shared DB; hash IDs
(`cn-a1b2` = blake2b of title+time+random, no central counter); atomic
write-temp-then-rename; `ready` = open issues with no open blocker; append-only
`.cairn/memory.jsonl` for `remember`/`prime`. CLI (`cairn init/create/ready/
claim/close/update/dep/remember/prime`, all with `--json`) + library
(`from cairn import Store; Store.discover()`). Deliberately drops: DB,
federation, tracker sync, LLM compaction, git hooks, telemetry.

Beads consumers = **stagehand** (`stg`) + **science-of-midtraining** (`smt`) —
BOTH FULLY MIGRATED 2026-07-02 on the committed-store convention: fresh
`cairn init --prefix <xx>` + `cairn import` (PR #2's importer, ids/statuses/
hierarchy preserved), validated `cairn ready` == `bd ready`, `.cairn/`
COMMITTED in-repo, README "Issue tracking" section added, local `.beads/`
DELETED. Stagehand = PR #23 (6 issues, epic stg-teu); sci-mt = PR #135 +
gitignore fix PR #136 (13 issues, epics smt-4hz/smt-yqi). Gotcha found in
sci-mt: a global `*.jsonl` gitignore silently untracks `.cairn/memory.jsonl`
— needs a `!.cairn/memory.jsonl` exception (PR #136). An earlier concurrent
session had made local-only (gitignored) stores with `.beads/` kept as
fallback; that convention was superseded by user sign-off on committed
stores, and its stray `cn`-prefix stores + uncommitted .gitignore edits were
cleaned up. No live Beads consumers remain.

Location: public at `dtch1997/cairn` (https://github.com/dtch1997/cairn),
gitignored clone at `repos/cairn` (NOT in jarvis tree, like the other spun-out
tools). v0.1.0 pushed to `main`, 16 tests passing, `pip install git+…`,
matching [[cherami-tool]] / [[reportly-tool]] /
[[databrowser-library-spun-out]]. NOTE: `gh` lives at `~/.local/bin/gh`
(2.94.0, authed as dtch1997) — NOT `/usr/bin/gh` which is absent; and commits
to public repos must use `dtch1997@users.noreply.github.com` or GitHub rejects
the push (email-privacy protection).

**2026-07-10:** moved into [[arsenal-monorepo]] as `packages/cairn` (history preserved); `repos/cairn` is now a symlink into `repos/arsenal`; dtch1997/cairn ARCHIVED with a pointer note.

**2026-07-10 (later): science-of-midtraining RETIRED its `.cairn/`** (PR #182,
user call — no migration; the 6 still-open issues are quoted in that PR's body).
This repo only for now — stagehand (`stg`) keeps cairn. Daniel floated
deprecating cairn generally in favour of **Linear** ("linear or something",
hedged); treat the old durable "in-repo agent-first tracker" preference as
UNDER REVISION — for new sci-mt follow-ups use Linear (project "Science of
Alignment Midtraining", team ARC) or PR descriptions, not cairn.
