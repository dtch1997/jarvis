---
name: scimt-aligne-infra-migration
description: "CLOSED 2026-07-23: scimt dropped the aligne dependency (vendor PR #231 MERGED) and is its own source of truth; aligne frozen (waves 1-3 dead weight on its side); no open follow-ups"
metadata:
  node_type: memory
  type: project
  originSessionId: 7cd2bec5-1ac6-47a8-8a56-8dff62e3b212
  modified: 2026-07-22T20:32:00.572Z
---

**REVERSED by Daniel 2026-07-22 evening** — after the migration waves AND the
idealised-docs/roadmap exercise, Daniel's call: *"drop the dependency on
aligne for now and have [[science-of-midtraining]] be the source of truth"*
(aligne has lots of unused surface; tired of maintaining it). Supersedes the
same-day decisions "teammates commit to aligne" and "aligne goes public"
(secret scan of aligne history ran clean 2026-07-22 — still true if the
public flip is ever revived).

**Why the reversal was cheap:** the scimt-side cutover NEVER happened — the
shim/pin-bump PR was always deferred, so scimt main kept its own copies of
everything the waves copied into aligne (checkpoint/remap/unlearn/health/
calibrate/publish/backends/axolotl/mix/runlog). Waves 1–3 all MERGED into
aligne (PRs #44/#45/#46) but nothing imports them; they're dead weight on
aligne's side, harmless. Roadmap PR #50 CLOSED unmerged (its 7 measurement
contracts + `sample` seam design remain good doctrine — repoint at scimt
when that work happens; content in the closed PR / session scratchpad).
Cleanup done: aligne worktrees docs-roadmap + pool-w3 removed, branches
deleted; the `release-0.8.0` worktree (jarvis-2's parallel attempt at the
same release) removed by jarvis-2 after the collision. NB aligne **v0.8.0
WAS released + tagged** (PR #52, includes waves 1–3, the py>=3.12 breaking
bump #51, and the CLI/DX + README polish #48/#49) — the freeze point is
v0.8.0, though scimt's pin still says v0.6.0 (both fine while frozen).
jarvis-2 confirmed the hold-off with Daniel 2026-07-22 before touching scimt.

**End state:** aligne FROZEN as a dependency (scimt pins v0.6.0 git tag);
scimt is source of truth for all its infra.

**Near-miss 2026-07-22 ~20:30 (jarvis-1):** unaware of the reversal, this
session dispatched concierge `t-0722-56d9` (scimt shims + pin bump to v0.8.0
— the OPPOSITE direction of the vendor task) right after merging wave 3 +
cutting v0.8.0. Caught via the rewritten memory stub and **CANCELLED** ~8 min
in: no PR, no branch, no worktree debris on scimt. Lesson: re-read the
project stub before dispatching follow-ups born earlier in a session —
parallel sessions can reverse direction mid-day. Also of note: aligne PR
**#53** (DESIGN.md R4 two-layer manifest, jarvis-1) was opened minutes before
the freeze surfaced — Daniel to merge or close given the freeze.

**Vendor extraction DONE — scimt PR #231 OPEN (needs Daniel's review/merge):**
worker `t-0722-fd69` completed + pushed the branch but FAILED at its $10
budget cap before opening the PR (lesson: $10 is too small for a ~2.5k-line
refactor with a mid-flight scope change; budget $25+ next time). Salvaged
in-session: merged post-prune main (clean), all 3 gates verified locally
(no aligne imports, no git dep, 460 passed under `--extra dev --extra gen`).
Original dispatch params: vendor FROM THE v0.6.0 TAG (what scimt's pin
runs; aligne v0.8.0 exists but is irrelevant), zero logic changes. Final
scope after Daniel's mid-flight cut (risk-averse constitutions moved to the
risk-averse-ai repo → scimt drops the constitutional path instead of
vendoring it; scope change sent via pool.msg): **vendor** `data.synthdoc` →
`scimt.gen.synthdoc` (+SynthdocConfig port if v0.6.0 predates it),
`util.client.ChatClient/Endpoint` → `scimt.utils.client`, `eval.inspect_sdf`
+ inspect_tasks + Tinker inspect provider → `scimt.eval` (watch the
inspect_ai provider entry-point registration — NB forks the battery shared
with [[model-thrashing-spun-out]], divergence accepted); **delete** from
scimt: train/distill.py, the 3 risk_* spec YAMLs, their 2 test files, the
constitution spec-kind wiring (experiments/ untouched, pin to history);
pyproject drops the aligne git dep, extra `[aligne]` → `[gen]`. Awaiter
backgrounded in session 42c7aec8.

**VENDOR MERGED — MIGRATION CLOSED (2026-07-23, scimt PR #231 squash-merged
9066cc7):** PR #231 was reconciled with the axolotl refocus (#238, which
landed in between) before merge: main merged into the branch; the worker's
vendored inspect_sdf + Tinker inspect provider and _rkl reverse-KL machinery
STRIPPED (their consumers were deleted by #238); Daniel's drop-the-
constitutional-path call finally implemented (the branch had vendored the 30
constitution JSONs anyway) — risk_* specs, gen/constitution.py,
spec_from_constitution, DocsSource.aligne_constitution and the "constitution"
spec kind all removed (persona kind + battery remain). Final vendored
surface: scimt.gen.synthdoc + scimt.utils.client (aligne v0.6.0 verbatim,
stdlib+httpx) — stage (i) needs NO extra; pyproject/uv.lock have zero aligne.
End state: scimt fully standalone; aligne frozen with no consumers here.
This stub is now historical — no open follow-ups.
