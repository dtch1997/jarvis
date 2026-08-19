# The sweep didn't skip those two PRs — it never enumerated them: the cutover repointed `github_repos` and left two lane-labelled PRs in repos nobody sweeps

*Investigation, 2026-08-18. Thread `figure-out-why-the-nightly-gazette-sweep`.*

## TL;DR

- The two affected PRs are **`ArcadiaImpact/jarvis#152`** (`lane:delay`, opened
  01:07Z) and **`dtch1997/life-theses#11`** (`lane:auto`, opened 08:24Z by the
  weekly thesis-review cron). Both are still open.
- **Neither has any row in `~/.gazette/log.jsonl`** — not `skip`, not `wait`,
  not `merge`, and not even a collector warning. They were never *decided*;
  they were never *seen*.
- **Root cause: repo scope, not lane logic.** The monorepo cutover *replaced*
  `github_repos` in `~/.config/gazette/config.toml` with `["dtch1997/jarvis"]`
  (file mtime 01:47:41Z) instead of extending it. `life-theses` was never in
  the list at all, even though its cron labels PRs `lane:auto` and logged "the
  nightly gazette sweep will pick it up from `lane:auto`". A PR outside
  `github_repos` is invisible: the sweep loops over configured repos only, so
  there is nothing to warn about.
- **A second, independent failure hit the same night**: the 03:29Z nightly
  sweep itself decided *zero* PRs (`[warn] dtch1997/jarvis: gh CLI not found`
  in `~/.claude/logs/gazette.log`) because it ran the pre-#24 code under cron's
  minimal PATH. That is issue #21's bug, fixed later the same day by #24 —
  **verified fixed** here by re-running the sweep under `env -i PATH=/usr/bin:/bin`.
- Fixes shipped (both needed — one is code, one is config):
  1. code: gazette now searches for lane-labelled PRs in repos it is *not*
     configured to sweep and reports each as an `unswept` spool row, a
     `[unswept]` sweep line, and a morning-edition **anomaly**;
  2. code: `config.DEFAULTS` repointed off the archived pre-cutover repos
     (`ArcadiaImpact/jarvis`, `dtch1997/arsenal`) onto the live set, with a
     regression test — the config file lives outside git, so DEFAULTS is the
     only in-repo migration guard;
  3. config (already live on the devbox): `github_repos = ["dtch1997/jarvis",
     "dtch1997/life-theses"]`, so `life-theses#11` merges at tonight's sweep.
- `#152` is **terminally stranded and needs no port**: its repo is archived
  (read-only — it can be neither merged nor closed), and its content (make
  `codex` the concierge pool default) was deliberately reverted at 01:37Z when
  codex workers turned out to be unable to push to GitHub.

## Questions — the four asked, answered

**Q1. Which two PRs were affected, and what are their characteristics?**
`ArcadiaImpact/jarvis#152` (`lane:delay`, touches only `CLAUDE.md`, opened
01:07Z, sits in a now-archived repo) and `dtch1997/life-theses#11`
(`lane:auto`, one thesis doc, opened 08:24Z by the weekly thesis-review cron).
Both are open and mergeable; neither is a draft, vetoed, changes-requested, or
touching a protected/credential path.

**Q2. Do they appear in `~/.gazette/log.jsonl` with a skip/wait/merge action?**
No — neither has any row at all, and no collector warning names them either.
This is absence, not a decision: they were never enumerated.

**Q3. What is the root cause — logic bug, PATH issue, API failure, or a
legitimate skip?** Repo scope. The monorepo cutover replaced `github_repos`
with the monorepo alone (config mtime 01:47:41Z), so both PRs live outside
everything the sweep looks at, and an unlisted repo cannot produce a warning.
Compounding it on the same night, the 03:29 nightly run decided *zero* PRs
because `gh` was unresolvable under cron's minimal PATH (pre-#24 code) — a real
PATH issue, but a separate and already-fixed one. Not a lane-policy skip, and
not a silent API failure at 13:59.

**Q4. Is a fix needed, or just clarification?** Both. A fix, because silence
here is a defect: the coverage detector, the repointed in-repo defaults, and the
live config repointing all ship. A clarification for `#152`, which is correctly
dead — archived repo, and its content (codex as the pool default) was reverted
hours before.

## Setup — how the two PRs were identified

The complaint was "the nightly sweep skipped two PRs", with no PR numbers. The
set was recovered by differencing every lane-labelled open PR against the sweep's
own spool:

```bash
# every sweep decision ever recorded, grouped by run
python3 - <<'PY'
import json
rows=[json.loads(l) for l in open('$HOME/.gazette/log.jsonl')]
by={}
for r in rows: by.setdefault(r['ts'],[]).append(r)
for ts in sorted(by): print(ts, len(by[ts]), sorted(r['number'] for r in by[ts]))
PY

# every open PR that claims a lane, across all of Daniel's owners
gh search prs --owner dtch1997     --state open --label lane:auto  --json repository,number,title
gh search prs --owner ArcadiaImpact --state open --label lane:delay --json repository,number,title
```

Exactly two lane-labelled open PRs have no spool row of any kind. Everything
else that was open during a sweep is accounted for.

## Result

### The two PRs

| PR | lane | opened (UTC) | files | checks | state | in `log.jsonl`? |
| --- | --- | --- | --- | --- | --- | --- |
| [`ArcadiaImpact/jarvis#152`](https://github.com/ArcadiaImpact/jarvis/pull/152) "CLAUDE.md: concierge pool defaults to codex backend" | `lane:delay` | 01:07:17 | `CLAUDE.md` | none | open, MERGEABLE, repo **archived** | **no row** |
| [`dtch1997/life-theses#11`](https://github.com/dtch1997/life-theses/pull/11) "Weekly thesis refresh 2026-08-18: geothermal" | `lane:auto` | 08:24:20 | `investment/theses/geothermal.md` | none | open, MERGEABLE | **no row** |

Neither is a draft, neither carries `veto`, neither has a changes-requested
review, neither touches a credential-like path. Under the lane policy
(`lanes.decide`), `#11` is a plain `merge` and `#152` a `wait`-then-merge — so
this was never a policy skip.

### Timeline of what the sweep actually did

| when (UTC) | run | repos enumerated | outcome |
| --- | --- | --- | --- |
| 00:28:31 | manual (gazette landing) | `ArcadiaImpact/jarvis`, `dtch1997/arsenal` | 5 decisions (3 merges, 1 wait, 1 blocked-skip) |
| 01:07:17 | — | — | `ArcadiaImpact/jarvis#152` opened (last write to that repo before archiving) |
| 01:47:41 | — | — | `config.toml` repointed to `["dtch1997/jarvis"]` — the old repo drops out with #152 still open |
| **03:29** | **nightly cron** | none | **0 decisions** — `[warn] dtch1997/jarvis: gh CLI not found` |
| 08:05 | notes cron | none reachable | false quiet edition: "Needs you (0)", "nothing merged" |
| 08:24:20 | — | — | thesis-review cron opens `life-theses#11` `lane:auto`, expecting the sweep |
| 13:24 | — | — | #24 merges: `~/.local/bin/gh` fallback + `PATH=` in `ops/cron.tab` |
| 13:59:01 / 13:59:08 | manual (`--dry-run`, then real) | `dtch1997/jarvis` | 12 decisions, 8 merged, 3 waits, 1 blocked-skip — `gh` worked from a session shell |

The 13:59 run is the one whose report a human would have read, and *within its
repo scope it is complete*: all 12 PRs open in `dtch1997/jarvis` at that
instant appear in the spool. That is why the miss looks like a "skip" — the
absent PRs are absent from the report itself, not marked skipped in it.

### Root cause 1 (the durable one): coverage is config, and the cutover narrowed it

`sweep.run` iterates `cfg.github_repos` and decides each PR it finds there.
There is no mechanism by which a PR in an unlisted repo can produce a row, a
warning, or an anomaly — the failure mode is *silence*, which is exactly the
class of bug issue #21 fixed one level down (a dead collector used to look like
a quiet day; now it is loud). The cutover replaced the repo list rather than
extending it, and nothing checked the residue:

- `ArcadiaImpact/jarvis` dropped out at 01:47 with #152 open;
- `dtch1997/life-theses` was never listed, though it has its own managed cron
  block and its cron explicitly delegates merging to the sweep (and even had to
  *create* the `lane:auto` label on that repo, a strong signal that the lane
  convention had spread further than gazette's config).

`config.DEFAULTS` had also gone stale in-repo: it still named both archived
pre-cutover repos, so a lost/recreated `config.toml` would have swept two dead
repos and reported a permanently quiet day.

### Root cause 2 (same night, independent): the nightly run enumerated nothing

The 03:29 cron run failed at the collector: cron's minimal PATH has no
`~/.local/bin`, the deployed gazette predated #24's `~/.local/bin/gh` fallback
(note the warning text lacks #24's "(searched PATH: …)" suffix), and the `PATH=`
line in `ops/cron.tab` landed only at 13:24. So every PR open at 03:29 was
missed, and the 08:05 edition rendered a false quiet day. Both halves of that
fix are now live and verified:

```console
$ env -i HOME=$HOME PATH=/usr/bin:/bin ~/jarvis-monorepo/.venv/bin/gazette sweep --dry-run
[would-merge] jarvis#32 (auto) — auto lane, checks green
...
$ crontab -l | grep -c '^PATH=/mnt/nw/home/d.tan/.local/bin'
1
$ jarvis-os/ops/install-cron.sh --check
cron block in sync with ops/cron.tab
```

### Ruled out

- **Lane policy / legitimate skip** — no draft, veto, changes-requested, or
  blocked-path condition applies to either PR (table above).
- **Silent `gh` API failure at 13:59** — that run's 12 rows match the 12 PRs
  GitHub reports as open at that timestamp.
- **cron/venv desync from the migration** — `install-cron.sh --check` is clean,
  the workspace venv was re-synced at 14:20, and every cron CLI path
  (`~/jarvis-monorepo/.venv/bin/{gazette,desk,threads,mailroom}`) resolves. The
  migration residue was in *gazette's own config*, not in cron or the venv.

## The fix

**Code (this PR).** Coverage is now checked, not assumed:

- `gh.search_lane_prs(owner, label)` / `gh.unswept_lane_prs(cfg)` — one
  `gh search prs --owner … --label lane:*` per watched owner, filtered to repos
  absent from `github_repos`.
- `sweep.run` spools each hit as `{"action": "unswept", "reason": "carries
  lane:auto but <repo> is not in github_repos"}` and prints `[unswept] …`;
  `cli._collect` feeds the same hits into the morning edition's **Anomalies**
  (a coverage gap, not a collector failure — the edition stays complete rather
  than INCOMPLETE).
- `watch_owners` config knob (default: the owners of `github_repos`), so
  repointing the sweep within an owner can no longer strand siblings silently.
- `config.DEFAULTS` repointed to the live repo set, with monorepo-aware *and*
  bare protected globs (a swept sibling repo has its own `ops/**`,
  `.claude/**`), guarded by `test_defaults_name_the_live_post_cutover_repos`.
- Docs: a "Coverage" section in the gazette README and a lane-labels-only-work-
  in-swept-repos paragraph in `jarvis-os/CLAUDE.md`.

Verified against real GitHub with the *pre-fix* config (`GAZETTE_HOME` pointed
at a throwaway spool):

```
[unswept] life-theses#11 (auto) — carries lane:auto but dtch1997/life-theses is not in github_repos
[warn] life-theses#11 carries lane:auto but dtch1997/life-theses is not in github_repos — no sweep will ever decide it
```

**Config (already applied on the devbox, `~/.config/gazette/config.toml`).**
`github_repos = ["dtch1997/jarvis", "dtch1997/life-theses"]`, bare protected
globs restored, `watch_owners = []` documented. With that in place the same
dry-run yields `[would-merge] life-theses#11 (auto)` and no stray warnings, so
`#11` merges at tonight's 03:29 sweep under the lane its author gave it.
`ArcadiaImpact` is deliberately *not* watched: the repo is archived, so #152
can never be merged or closed and the warning would be permanent and unfixable.

**No fix for `#152` — it is correctly dead.** Its diff adds a "pool defaults to
codex" paragraph to the pre-cutover `CLAUDE.md`; the codex default was reverted
at 01:37Z (codex workers can't git-push, jarvis issue #8) and the monorepo
`CLAUDE.md` deliberately says nothing about a codex default. Porting it would
re-document a reverted decision.

## Takeaway

Consumer mode's trust property is "silence means nothing happened", and it only
holds if every way of producing silence is instrumented. Issue #21 fixed the
first way (a dead collector inside a configured repo). This was the second way,
one level up: a repo the config never mentions. Both have the same shape — an
empty result that is indistinguishable from a quiet day — and both need the
same treatment: prove coverage, don't assume it. The generalization worth
keeping is that **any per-machine config file outside git is a migration
hazard**; the in-repo defaults are the only thing that can flag drift, so they
have to be kept honest and tested.

## Next steps

- Watch tomorrow's edition (2026-08-19): `life-theses#11` should appear in the
  news as merged by the 03:29 sweep, and no `unswept` rows should be spooled
  (`grep unswept ~/.gazette/log.jsonl`).
- After this PR merges, the 04:10 deploy cron pulls it into
  `~/jarvis-monorepo` and re-syncs the venv, so the coverage detector goes live
  that night — no manual deploy needed.
- Optional, Daniel's call: `#152` can be left to rot with its archived repo
  (recommended — the codex default it documents was reverted), and the same
  goes for any other pre-cutover PR; nothing in the archived repo can be
  merged or closed anymore.
- If a future repo starts using lane labels, add it to `github_repos` in the
  same pass; the new `unswept` anomaly is the backstop, not the process.

## Reproduce

```bash
# 1. the two PRs with no spool row (needs gh auth; set -a; . ~/.env; set +a)
gh pr view 152 -R ArcadiaImpact/jarvis --json number,labels,isDraft,files,statusCheckRollup
gh pr view 11  -R dtch1997/life-theses --json number,labels,isDraft,files,statusCheckRollup
grep -c 'life-theses\|ArcadiaImpact/jarvis", "number": 152' ~/.gazette/log.jsonl   # → 0 before the fix

# 2. the failed nightly run
grep 'gh CLI not found' ~/.claude/logs/gazette.log
python3 -c "import json;print({json.loads(l)['ts'][:16] for l in open('$HOME/.gazette/log.jsonl')})"  # no 03:29 run

# 3. the fix, offline
cd jarvis-os/packages/gazette && PYTHONPATH=src python -m pytest tests -q     # 37 passed

# 4. the fix, live (throwaway spool; use a config.toml WITHOUT life-theses to see the warning)
mkdir -p /tmp/gz/.config/gazette && cp ~/.config/gazette/config.toml /tmp/gz/.config/gazette/
GAZETTE_HOME=/tmp/gz PYTHONPATH=jarvis-os/packages/gazette/src \
  ~/jarvis-monorepo/.venv/bin/python -m gazette.cli sweep --dry-run
```

## Provenance

- Investigated and written by concierge worker `t-0818-a49a`, branch
  `figure-out-why-the-nightly-gazette-sweep/dz7cmh9a`, intent
  `01M0AT0PASYM69XT5SDZ7CMH9A`.
- Evidence read: `~/.gazette/log.jsonl` (17 rows across 3 runs at
  investigation time), `~/.gazette/editions.jsonl`, `~/.gazette/notes/2026-08-18.md`,
  `~/.claude/logs/{gazette,deploy,thesis-review}.log`, `crontab -l`,
  `jarvis-os/ops/cron.tab`, `~/.config/gazette/config.toml` (mtime 01:47:41Z),
  `~/.desk/state.json`, and `gh pr list` for `dtch1997/{jarvis,arsenal,life-theses}`
  + `ArcadiaImpact/jarvis`.
- Two `--dry-run` sweeps during the investigation appended `dry_run: true` rows
  to the real `~/.gazette/log.jsonl` (16:14Z, 16:17Z) — the cron-PATH
  reproduction and a spot check; the coverage smoke tests used throwaway
  `GAZETTE_HOME` spools. No merges were performed. No GPU/pod spend.
