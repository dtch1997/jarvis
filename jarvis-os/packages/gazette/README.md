# gazette

Consumer-mode PR flow: Daniel reads morning **patch notes** about what merged
instead of reviewing every PR. Agents declare a lane on each PR at open time;
a nightly sweep merges what the lane allows; a veto is one label away.

## Lanes (GitHub labels)

| label          | what belongs here                                   | cron behavior                        |
| -------------- | --------------------------------------------------- | ------------------------------------ |
| `lane:auto`    | docs, drafts, wiki, dashboards, memory-adjacent     | merged nightly on green checks       |
| `lane:delay`   | conventions (CLAUDE.md), ops/cron.tab, tool behavior | merged after appearing in 2 morning editions unless vetoed |
| `lane:blocked` | money, credentials, external-facing, destructive     | never cron-merged — desk/flare flow  |

- **Unlabeled** PRs default to `lane:delay` and are flagged as unclassified.
- **Demotions are the backstop**: an auto-labeled PR touching protected paths
  (`CLAUDE.md`, `ops/**`, `.claude/**`, …) drops to delay; anything touching
  credential-like paths (`.env*`, `*secret*`, `*credential*`) drops to blocked
  — regardless of label. Demotions appear in the patch notes as anomalies.
- **Veto** = add the `veto` label or request changes on the PR. Drafts are
  never touched.

## CLI

```
gazette sweep [--dry-run]   # nightly merge pass (squash; deletes remote branch,
                            # leaves local worktrees to sessions)
gazette notes [--flare]     # morning edition → stdout + ~/.gazette/notes/YYYY-MM-DD.md
gazette status              # one-line digest
```

The edition is deadline-first — closable the moment the top section is empty:
*Needs you* (veto-window items with their default outcome + a copy-pasteable
veto command, blocked PRs, and the folded-in `desk digest`) · *Anomalies*
(unclassified PRs, demotions, failing checks — only when non-empty) · *News*
(an LLM pass groups the last 24h of merges into "you can now …" bullets via
headless `claude -p`, falling back to the flat list on any failure; the flat
list always follows) · *In the pipeline* (ambient, nothing to do). A quiet
morning flares as a one-liner.

**Veto windows count delivered editions, not wall-clock hours**: each
`gazette notes` run logs which PRs it showed (`~/.gazette/editions.jsonl`,
distinct dates only), and a delay-lane PR merges after appearing in
`delay_editions` (default 2) editions. A skipped morning — weekend, broken
cron — pauses the window instead of letting conventions merge unseen; a PR
aged far past the window with too few editions raises a stall anomaly.

## Coverage — the sweep only sees the repos it is told about

`github_repos` is the whole world as far as the sweep is concerned: a PR in
any other repo gets no decision, no log row, and no warning. That bit on
2026-08-18, when the monorepo cutover *replaced* the repo list — `life-theses#11`
(`lane:auto`, opened by the weekly thesis-review cron) and the archived
`ArcadiaImpact/jarvis#152` (`lane:delay`) simply never appeared anywhere.

So every sweep/edition also **searches for lane-labelled open PRs in repos it
is not configured to sweep** (`gh search prs --owner … --label lane:*` over
`watch_owners`, default: the owners of `github_repos`). Each hit becomes an
`action: "unswept"` row in the spool, a `[unswept]` line in the sweep report,
and a morning-edition *anomaly* — a coverage gap, not a collector failure, so
it does not mark the edition INCOMPLETE. The fix for such a warning is either
adding the repo to `github_repos` or dropping the lane label.

Config: `~/.config/gazette/config.toml` (created with commented defaults on
first run) — repos, `watch_owners`, `delay_hours` (stall detector),
`delay_editions`, `synthesis_cmd` (`""` disables the news pass),
protected/blocked globs. The file lives outside git, so `config.DEFAULTS` is
the migration guard: keep it naming the live repo set.
Spool: `~/.gazette/log.jsonl` (every sweep decision, plus `unswept` rows),
`~/.gazette/notes/`, `~/.gazette/editions.jsonl`.

Uses the `gh` CLI for all GitHub access (existing auth); sends the morning
digest through `flare`. Policy lives in pure functions (`lanes.decide`) so the
whole merge policy is offline-testable.
