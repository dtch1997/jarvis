---
name: self-driving-jarvis
description: Direction layer for jarvis — goals/ registry + propose-only /goal-review planner; milestone ladder toward autonomous goal-driven dispatch
metadata: 
  node_type: memory
  type: project
  originSessionId: 45fdfba4-7e20-43a1-943f-2a8fadc8870a
  modified: 2026-08-18T14:30:51.149Z
---

Initiative to make jarvis goal-driven: Daniel specifies high-level goals,
agents plan/spec/dispatch against them. Execution layer ([[concierge-tool]],
[[stagehand-spun-out]], arch2) already existed; the gap was a direction layer,
and the crux is autonomous spec-writing quality
([[experiments-need-spec-not-permission]]).

**Status 2026-07-17**: milestone 1 shipped as jarvis PR #112 (branch
goal-registry, worktree still up pending review) — `goals/` registry
(README format spec + TEMPLATE + seeded DRAFT goals) + propose-only
`/goal-review` skill + CLAUDE.md pointer. 2026-07-20: pruned per Daniel to a
single goal — self-driving-jarvis (durable-organisms, trait-science, and
science-of-midtraining removed; recoverable from git history at 76a90c2 on
branch goal-registry). Seeded Vision/rubric/budget are
agent drafts awaiting Daniel's edit (DRAFT banners in each file).

**Design decisions**: ownership split — Daniel owns Vision/rubric/budget/
`automation` flag, agents own Frontier/Active threads/Parked follow-ups
(dated bullets). Planner is propose-only until spec quality earns trust;
per-goal `automation: propose-only|dispatch` flag flips one goal at a time
with hard budget caps. Reviews land in goals/reviews/YYYY-MM-DD.md via PR
with checkbox veto; every cycle must report even when idle.

**Status 2026-08-15 — command-center reframe + Daniel-stated goals**: jarvis
explicitly reframed as a *command center for high-throughput AI work* —
design doc `docs/command-center.md` on PR #117 (seven layers: direction /
state / execution / observability / attention-routing / review / resources;
weakest = attention routing + review; ranked build order = waiting-on-Daniel
inbox → build [[flare-proposal]] → activity journal (project-journal scanner
as arsenal pkg over memory registry, worktree-branch→slug matching) → merge
#112 → review-debt tooling → resource ledger). Same day Daniel stated four
goals (thesis shape-up, ARC WHEST blogpost, [[power-concentration-post]],
dogfight-rl release) — transcribed into goals/ on the goal-registry branch
(PR #112 updated). **MERGED 2026-08-15 (d92b7a7) under new draft-and-veto
ownership** (Daniel: "don't bottleneck on a complete direction — have agents
brainstorm/propose"): agents draft everything incl. Vision/rubric/new goals
(provenance marker `agent-drafted, standing until Daniel edits`), drafts
immediately operative; ONLY `automation: dispatch` + real budgets wait for
Daniel. Agents may add `status: incubating` goals. DRAFT banners abolished.
Merge gotcha hit: gh pr merge right after pushing a merge commit → "not
mergeable" (mergeability recompute); deleting the remote branch then CLOSES
the PR — restore branch + `gh pr reopen` + retry worked. Open design
decisions Daniel explicitly has no strong takes on yet (treat my defaults as
standing proposals): auto-merge-with-veto for experiment-wrapup PRs, inbox
push cadence, one-queue-vs-two for goal-review proposals, per-PR review
briefs.

**Rubric-must-discriminate principle** (Daniel, 2026-07-20): rubric bullets
earn their place only if they can change a ranking between candidate
proposals; universal safety invariants (external gates, report-even-when-idle,
hard budgets) belong in enforcing machinery (skill hard rules, SOP, knobs),
not restated in rubrics.

**Recognizer-not-roadmap principle** (Daniel, 2026-07-20): Definition of
progress sections state how to *recognize* progress; they never encode a
milestone plan. Plans are derived dynamically each cycle from repo state and
live in the agent-owned Frontier/Active-threads sections, revisable. Current
working plan (revisable): registry (DONE, pending merge) → groundskeeper cron
sweeping parked follow-ups into concierge → /goal-review on a cron,
propose-only, Daniel grades specs → gated dispatch. Open question: mirror
goals into Linear initiatives vs files-as-source-of-truth.

2026-08-16: attention-routing build dispatched to concierge (t-0816-5bed) and gate-passed → arsenal PR #42 (flare + desk). Jarvis PR backlog cleared to ZERO (merged 124/116/115/114; closed 113/100/97/90 per meta-level policy). Apollo thread deprecated by Daniel → memory archived. RunPod balance handled by auto top-up (Daniel).

**2026-08-17 — bottom-up threads philosophy + loom spec**: Daniel stated a
philosophy update (captured in [[bottom-up-direction-philosophy]]): direction
is bidirectional (bottom-up discovery from work patterns is valid alongside
goals/), AI may auto-generate threads, veto = delete/rework. Branch
`threads-bottom-up` → **jarvis PR #136 MERGED** (c152a87; worktree cleaned): amends command-center.md (new "Threads — the bottom-up spine"
section; flare/desk marked shipped) + new `docs/threads.md` = MVP spec for
**threads** (arsenal pkg; Daniel renamed from "loom" — collides with
existing AI term): scan (haiku summaries of ~/.claude/projects
transcripts) → weave (branch→slug, concierge-tid-from-cwd, repo→slug;
unfiled inbox + agent-drafted candidate threads) → serve (lobby dashboard:
thread table w/ dormancy, drill-down, inbox, candidates). DoD gate-checkable
(≥70% auto-match, no-op rescan <10s, spend reported). **Build DONE same day: t-0817-75e8
gate-passed → arsenal PR #48 OPEN** ($18.7 worker + ~$5.7 haiku backfill):
47 tests green; 30-day backfill = 284 sessions (120 model summaries + 164
trivial stubs); **82% deterministic match** (key insight: dominant
touched-repo from tool-use paths + PR refs — cwd/branch alone only ~20%);
25/25 concierge sessions resolved; 2 candidate threads auto-drafted;
dashboard live in tmux `threads-dashboard` via lobby /a/threads/. Worker
gotchas (in PR #48): summarizer's own `claude -p` calls polluted
~/.claude/projects → CLAUDE_CONFIG_DIR isolation + self-reflection filter;
scan --check tolerates size-drift on live transcripts. Daniel approved →
**PR #48 MERGED (cff0902)**. Same day, Daniel's v0.2 asks → **dispatched
t-0817-5d15**: (1) thread-table sort/filter + relevance =
w_s·log1p(sessions) + w_r·exp(-age/τ) in config.toml (formula isolated,
refinable); (2) recursive hierarchy — ~/.threads/hierarchy.md (agent-drafted
tree), goal roots parsed read-only from jarvis/goals/, auto-drafted
programs, roll-ups + collapsible tree view + threads↔goals coverage panel;
(3) Obsidian-compatible vault mirror ~/.threads/vault/ (frontmatter +
wikilinks, regenerable view, JSON spool stays truth — Daniel's call: format
compatibility now, vault-sync workflow = experiment; standing proposal =
**arsenal issue #49**, verdict criterion: vault beats lobby dashboard after
~2 weeks of use → deepen, else stop). Remaining phase 2: stub activity
blocks, desk integration.

**2026-08-17 — threads push channel (note/pickup)**: Daniel's use case —
mid-session "moving on, park this durably for review + pickup" → built
`threads note <slug> [text|-]` (markdown+frontmatter context-dump into
~/.threads/notes/<slug>/; auto-captures cwd/branch/CLAUDE_SESSION_ID;
unregistered slug seeds a candidate thread) + `threads pickup <slug>`
(rehydration pack: registry line → notes → observed sessions); notes count
as dashboard activity (suppress false dormancy). **arsenal PR #50 OPEN**
(57 tests green) + **jarvis PR #137 OPEN** ("park" keyword + parking
convention in CLAUDE.md attention-routing, section retitled flare+desk+
threads; docs/threads.md addendum). Caution: t-0817-5d15's v0.2 work also
edits dashboard.py → whichever PR merges second likely needs a rebase.
Gotcha: arsenal root .venv's editable `threads` points at the t-0817-5d15
concierge workspace, not repos/arsenal — run worktree tests with
PYTHONPATH=src.

**2026-08-17 — threads v0.2 DONE: t-0817-5d15 gate-passed → arsenal PR #51
OPEN** ($11.45 worker, ~$0.15 model): 85 tests; relevance sort/filter live
(pure relevance() + ~/.threads/config.toml knobs); recursive hierarchy
(hierarchy.md tree, goal roots parsed from jarvis/goals/, 3 auto-drafted
programs: aligne/arch2/arsenal, roll-ups + tree view + coverage panel);
Obsidian vault at ~/.threads/vault/ (31 threads/123 sessions/5 goals,
INDEX.md, auto-run after weave). Top-5 relevance: science-of-midtraining
5.78, arsenal-monorepo 5.09, safety-desert 4.70, phd-thesis 4.41,
arc-whest 4.14. Coverage finding: 27 threads under no goal. **MERGE-ORDER
CAUTION: PR #50 (note/pickup, other session) and PR #51 (v0.2) both edit
dashboard.py — second to merge needs rebase.** PR #51 awaits Daniel review.

2026-08-17 (later): **all three threads PRs MERGED** — arsenal #51 (v0.2),
arsenal #50 (note/pickup; I rebased it over #51's dashboard.py — additive
union, 95 tests green), jarvis #137 ("park" keyword + convention in
CLAUDE.md). Worktrees/branches cleaned, arsenal venv re-synced, fresh
scan+weave (292 sessions, 89% match), dashboard restarted on merged build
(200 OK). Not yet done: threads cron line in ops/cron.tab (daily scan+weave
+ vault); flare Slack webhook still unconfigured.

2026-08-18 wrap-up: README rewrite for 3rd parties MERGED (arsenal #53);
daily 07:19 scan+weave cron MERGED+INSTALLED (jarvis #139, --check green);
blogpost parked by Daniel onto thread `arsenal-tooling-blogpost` (threads
note; in-flow refinement pattern: append notes as material appears →
periodic concierge fold-in); goal file refreshed with dated bullets (#143,
incl. BLOCKED-ON-DANIEL: flare webhook). All session worktrees clean except
arsenal-blogpost (deliberate, serves cowrite).

2026-08-18 (consumer mode): **merge lanes + patch notes BUILT** — Daniel's
call: he's a consumer of JARVIS software, reads morning patch notes instead
of reviewing PRs. `gazette` arsenal package (arsenal PR #65): nightly
lane-respecting sweep (`lane:auto` merge-on-green / `lane:delay` 36h veto
window / `lane:blocked` never; demotion backstops on protected+credential
paths; veto = label or changes-requested) + morning `gazette notes --flare`.
Jarvis PR #144: CLAUDE.md "PR lanes" convention (label every PR at open),
cron.tab entries (sweep 03:29, notes 08:05), docs/morning-routine.md sketch
(patch notes = component 1; v2 = single morning page, open questions for
Daniel). Labels created+applied to open PRs on both repos. BOOTSTRAP: both
PRs are lane:delay — after merge run `uv sync --all-packages` in
repos/arsenal + `ops/install-cron.sh`.

2026-08-18 (morning routine v2, SG'd): **edition-first patch notes BUILT** —
arsenal PR #73 (gazette v2: Needs-you-first w/ default outcomes + veto cmds,
desk digest folded in, anomalies only when non-empty, LLM "you can now …"
news via headless `claude -p --model sonnet` w/ flat-list fallback,
quiet-morning one-liner flare; **veto window = 2 delivered editions** via
~/.gazette/editions.jsonl — skipped mornings pause it, `delay_hours` kept as
stall detector) + jarvis PR #150 (docs/morning-routine.md v2, retire 08:35
desk→flare cron, CLAUDE.md lane wording, goal bullet, **new 04:10 deploy
cron** — closes the merged-code-has-no-deployer gap: pull pinned mains +
`uv sync` + link-clis + install-cron nightly). **MERGED +
DEPLOYED same day** — Daniel merged both during the monorepo cutover
([[jarvis-monorepo-migration]]); deploy cron + retired desk cron confirmed
live in crontab, gazette config repointed to dtch1997/jarvis
(protected_globs cover jarvis-os/ops + jarvis-tools/packages), v2 code
verified via dry-run sweep. Old-world editions.jsonl seed removed (refs
would collide with monorepo PR numbers) — edition counting starts fresh
2026-08-19. Worktrees cleaned from ~/jarvis-old + ~/arsenal-old-clone.
Next: mailroom reply-to-veto + 👍 read-ack = **monorepo issue dtch1997/
jarvis#3** (re-filed; arsenal#74 archived read-only). Watch item: first v2
edition lands 2026-08-19 08:05 — check needs-you section, synthesis
quality, desk fold-in, editions.jsonl appending.

2026-08-18 (philosophy note): Daniel's consumer-mode stance written up as
**drafts/consumer-of-your-own-software.md** (jarvis #151, MERGED in the
cutover drain; lives in monorepo jarvis-os/drafts/). Thesis: premise obvious
(vibe coding = the stance locally), implications are the content — agents
file issues/write PRs/engineer loops; legibility budget goes to *behavior*
(behavior-delta describability, observable contracts as spec, cheap
"works-today?" checks, rollback as product feature); patch notes = a
*forcing function* + the dial generalizes as (cadence, rollback unit,
feedback channel). Companion philosophy doc to the gazette machinery;
candidate blogpost material (cf. [[bottom-up-direction-philosophy]]).

2026-08-18 (thread launcher, SG'd): Daniel's UX critique of the Claude Code
front door (couples intention+implementation; sequential) → design convo →
**thread = atomic primitive of work; launcher = intentional birth of
threads** (complement to observational scan/weave). Spec MERGED-or-pending
as **monorepo PR dtch1997/jarvis#6** (lane:auto):
jarvis-os/docs/thread-launcher.md + command-center.md wiring (threads
section + build-order 4b "fills the entry-into-layer-3-is-manual gap,
message-inward"). Key contracts: send = <100ms durable intent record, all
else async onto the thread; router auto-attaches to existing slug
(Daniel's explicit call, no confirmation) else mints candidate thread;
mode at entry, **full-auto default** (concierge, router-drafted gate) /
copilot (seeded tmux+foyer); slug stamped at spawn (THREADS_SLUG env +
`<slug>/<ulid>` branch + note zero) → deterministic weave pre-pass;
**termination contract** (every launched thread reaches terminal note
result/blocked/failed, else desk pages); surfaces = `threads launch` CLI +
POST /launch + dashboard pane; mailroom/Slack = future transports into the
same endpoint. Implementation = **monorepo issue dtch1997/jarvis#7**
(jarvis-os/packages/threads since the os/tools boundary move, PR #11;
good concierge dispatch candidate). **Build DONE same day: t-0818-b571
gate-passed → monorepo PR #14 OPEN (lane:delay)** — 118 tests (95
existing + 23 new), accept 9.6–16ms (<100ms), launcher-stamp weave
pre-pass (unit-covered; 0/0 live until a launcher-born session is
scanned), termination sweep → desk+flare, full-auto gate menu in README
(repo-shaped=PrOpen / question-shaped=result-file ShellOk / &-composed
for compute), real bounded smokes (full-auto t-0818-4a39 settled via
gate-WRITTEN terminal note; copilot tmux verified+killed). First
dispatch t-0818-0611 FAILED on the codex default-backend gotcha (issue
#8): submitted 3 min before the config fix; codex sandbox has no
network/tmux and its claimed commits didn't exist — the PrOpen gate
caught the false self-report; redispatched backend="claude" with an
untrusted-salvage note (worker dropped the codex draft's concierge-core
scope creep). **MERGE-ORDER CAUTION: PR #11 (os/tools boundary move)
vs PR #14 both touch packages/threads — second to merge needs a rebase
(flagged on both PRs).** Spec PR #6 (lane:auto) awaits gazette sweep;
worktree .claude/worktrees/thread-launcher-spec cleanup owed
post-merge.

**2026-08-18 — auto-wrapup spec (threads sweep)**: Daniel's ask — threads
>1wk old should be handled if forgotten. Spec = docs/auto-wrapup.md
(**monorepo PR #19, lane:auto**): daily deterministic sweep (no model
calls), stale>7d classified A1 mechanical-abandoned (→ concierge wrap-up,
gated by new `threads sweep --verify <slug>`) / A2 dirty-worktree (never
auto-touched) / B parked-and-forgotten >21d (disposition proposal);
mode=report default, dispatch flip = Daniel (goals automation-flag
pattern), max 2 dispatches/run + cooldowns; backstop to the launcher
termination contract. Impl = **issue #20**, blocked on PR #11 AND PR #14
(both touch packages/threads; #14 already ships a termination sweep the
impl should extend, not duplicate — noted on the issue). Not dispatched.

**2026-08-18 — background-thinking trial (Daniel-approved)**: jarvis gets
idle-time cognition — spec docs/background-thinking.md via **monorepo PR
#31 (lane:delay)**. Rung 1: /goal-review finally cron'd (weekly Tue 06:45,
propose-only — starts the graded-spec track record the dispatch flag waits
on). Rung 2: new **watchman** skill (.claude/skills/watchman/SKILL.md),
6-hourly (01:45/07:45/13:45/19:45; 07:45 feeds the 08:05 edition) —
propose-only judgment over goal frontiers/threads render/desk digest/PRs/
flares/git log; ≤3 observations per run as one batched info flare + threads
notes; silent default; 7-day no-repeat via ~/.watchman/ spool; only writes
= spool/notes/flares. Cadence rationale (Daniel asked): noticing improves
with fresh input → 6h; proposing improves with graded feedback → weekly.
Rung 3 (per-goal automation:dispatch + budget) explicitly not moved.
~2-week verdict ≈ 2026-09-01 (criteria in spec: acted-on observations vs
edition-restating/alert-fatigue/total-silence). Hardening path: skill+cron
trial → jarvis-os/packages policy tool only if it accretes state worth
owning.
