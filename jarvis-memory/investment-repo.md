---
name: investment-repo
description: "Personal investment-thesis repo (dtch1997/investment, PRIVATE, clone repos/investment) — thesis files, core-satellite policy, quarterly reviews"
metadata: 
  node_type: memory
  type: project
  originSessionId: c0c03a9a-f734-490c-83df-18ba1821df07
  modified: 2026-08-16T12:01:14.128Z
---

Personal investing project, scaffolded 2026-08-16: **dtch1997/investment**
(PRIVATE — personal finance), clone at `repos/investment`.

Structure: `theses/` (one file per thesis, TEMPLATE.md; lifecycle
draft/active/parked/falsified/closed; the Edge section — "why hasn't the
market priced it" — is the gate), `portfolio/` (policy.md = core-satellite
rules, holdings.md = position→thesis mapping), `reviews/` (quarterly,
propose-only à la /goal-review), `research/QUEUE.md` (backlog).

Operating policy: 80–90% core (broad index, never touched) / 10–20%
thesis sleeve; no satellite position without an active thesis file;
default instrument shares, options = LEAPS-only with named timeframe +
IV disagreement. Draft-and-veto ownership like [[self-driving-jarvis]]
goals/: agents draft theses/reviews freely; **moving real money and
changing the core-satellite split always wait for Daniel**.

Seed theses: null-hypothesis (core, active), long-ai (ACTIVE — AIS ETF),
geothermal (draft, actionable).

Research passes 1–2 done 2026-08-16 (PR #1): **(1) AIS teardown → KEEP**:
AIS = VistaShares AI Supercycle (NYSE, ER 0.75%) is NOT a Mag-7 rebuy —
~3% Mag-7 vs ~34% VOO, ~90% differentiated/dollar, already the bottleneck
basket incl. datacenter-energy leg; +158% since 12/24 inception (~24%
memory/HBM overweight already paid — high-beta cyclical); tripwire =
Mag-7 >15% at semi-annual rebalance. **(2) Geothermal → expression
problem obsolete: Fervo IPO'd as FRVO (Nasdaq, 2026-05-13)**; $20 vs $27
IPO on multiple compression, 658 MW PPAs/$7.2B backlog; ORA = partial
play; entry decision targeted at **FRVO lockup ~Nov 2026** conditional on
Cape Station (100 MW by early 2027 = make-or-break).

Infra (2026-08-16, PRs #2–#6 all merged): broker-API research —
tastytrade has full OAuth2 Open API (tastyware SDK v13, TT_SECRET/
TT_REFRESH env), POEMS B2B-gated → statement parse, Endowus no API →
PDF/manual. `scripts/tastytrade_snapshot.py` (uv single-file, read-only
→ portfolio/snapshots/) built + logic-tested; live run blocked on
Daniel's OAuth grant (**issue #4**). **Self-driving loop LIVE**: repo
CLAUDE.md + `.claude/skills/thesis-review/SKILL.md` (refresh/review
modes, propose-only, [trigger] escalation as PR+issue, strict Edge gate
on new-thesis proposals) + crontab: weekly refresh Tue 08:19, monthly
review 1st 09:03, flock-serialized, logs →
~/.claude/logs/thesis-review.log. **Crontab is a build artifact** (PR
#7, per Daniel's IaC preference): source of truth = `ops/cron.tab`,
`ops/install-cron.sh` reconciles a marked block (idempotent, `--check`
= drift detect, wired into weekly refresh); never hand-edit the block.
Daniel would likely want the same treatment for the OTHER jarvis crons
eventually (memory-consolidate/pod-audit/habitat live only in crontab).
Gotcha: `--delete-branch` half-fails in this repo too (worktree
convention).

Next: Daniel does issue #4 (OAuth grant) + backfills holdings + sets
split; queue = core composition (S&P vs global) + FRVO entry-prep
(~Oct/Nov 2026). Todoist has an "Investment" project (id 6gwfrPpMFCXmhJ46).
