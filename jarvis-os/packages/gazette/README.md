# gazette

Consumer-mode PR flow: Daniel reads morning **patch notes** about what merged
instead of reviewing every PR. PRs merge on green at an hourly sweep; the box
runs a **named nightly version** and anything that shipped can be rolled back
with one command. (The 2026-08-19 rework: merge-on-green + versions replaced
the old three-lane model with its delay windows.)

## Lanes

| lane | how a PR gets it | cron behavior |
| ---- | ---------------- | ------------- |
| auto (default) | no label needed (`lane:auto` accepted but redundant) | merged at the next hourly sweep once checks are green |
| requires-approval | `requires-approval` label, or touching credential-like paths (`.env*`, `*secret*`, `*credential*`) regardless of label | never cron-merged — desk/flare flow |

- Legacy labels: `lane:blocked` is an alias for requires-approval;
  `lane:delay` is retired — a PR carrying it merges as auto and the edition
  notes it as an anomaly.
- **Behavior-shaping annotation**: merges touching `CLAUDE.md`, `ops/**`,
  `.claude/**`, workspace packages, … merge like anything else but are
  annotated in the sweep log and edition — versioning is the rollback, not a
  delay.
- **Veto** (pre-merge) = add the `veto` label or request changes on the PR.
  Drafts are never touched. Post-merge remedy = version rollback or a revert
  PR.

## Versions — nightly cuts, switchable

Merges land on main all day; the *box* changes once per night. The 04:10
cron runs `version cut` (tag `origin/main` as `vYYYY.MM.DD`, pushed; same-day
re-cuts get `.2`, `.3`, …) then `version deploy` (pull the deployed checkout
forward — or honor a rollback pin — and run `deploy_cmds`: `uv sync`,
`link-clis.sh`, `install-cron.sh`, so venv/CLIs/crontab always match the
deployed tree).

```
gazette version cut          # tag origin/main tip as tonight's version (idempotent)
gazette version deploy       # deploy pin-or-main + run deploy_cmds
gazette version switch v2026.08.15   # ROLLBACK: pin the box to that version
gazette version switch latest        # resume nightly tracking
gazette version list|status  # what exists / what the box is running
```

A pin survives nightly deploys until cleared (the deploy just re-asserts it),
and rolls back CLAUDE.md, crons, and CLIs together — the box never runs a
state without a name. Pin state: `~/.gazette/version-pin`.

## CLI

```
gazette sweep [--dry-run]   # hourly merge pass (squash; deletes remote branch,
                            # leaves local worktrees to sessions)
gazette notes [--flare]     # morning edition → stdout + ~/.gazette/notes/YYYY-MM-DD.md
gazette status              # one-line digest
gazette version …           # see above
```

The edition is deadline-first — closable the moment the top section is empty:
*Needs you* (requires-approval PRs with a copy-pasteable approve command, and
the folded-in `desk digest`) · *Anomalies* (demotions, retired labels,
failing checks — only when non-empty) · *News* (an LLM pass groups the last
24h of merges into "you can now …" bullets via headless `claude -p`, falling
back to the flat list on any failure; the flat list always follows) · *In the
pipeline* (ambient: auto PRs on their way to the next sweep, each with a veto
escape hatch). It names the running version. A quiet morning flares as a
one-liner.

## Coverage — the sweep only sees the repos it is told about

`github_repos` is the whole world as far as the sweep is concerned: a PR in
any other repo gets no decision, no log row, and no warning. That bit on
2026-08-18, when the monorepo cutover *replaced* the repo list — `life-theses#11`
(opened by the weekly thesis-review cron) and the archived
`ArcadiaImpact/jarvis#152` simply never appeared anywhere.

So every sweep/edition also **searches for lane-labelled open PRs in repos it
is not configured to sweep** (`gh search prs --owner … --label …` over
`watch_owners`, default: the owners of `github_repos`; legacy labels
included). Each hit becomes an `action: "unswept"` row in the spool, a
`[unswept]` line in the sweep report, and a morning-edition *anomaly* — a
coverage gap, not a collector failure, so it does not mark the edition
INCOMPLETE. The fix is either adding the repo to `github_repos` or dropping
the label.

Config: `~/.config/gazette/config.toml` (created with commented defaults on
first run) — repos, `watch_owners`, `synthesis_cmd` (`""` disables the news
pass), protected/blocked globs, `checkout` (the deployed checkout `gazette
version` manages), `deploy_cmds`. Old configs with retired keys
(`delay_hours`, `delay_editions`) still load; the keys are ignored. The file
lives outside git, so `config.DEFAULTS` is the migration guard: keep it
naming the live repo set.
Spool: `~/.gazette/log.jsonl` (every sweep decision, plus `unswept` rows),
`~/.gazette/notes/`, `~/.gazette/editions.jsonl` (delivery log),
`~/.gazette/version-pin`.

Uses the `gh` CLI for all GitHub access (existing auth) and plain `git` for
versions; sends the morning digest through `flare`. Policy lives in pure
functions (`lanes.decide`) so the whole merge policy is offline-testable.
