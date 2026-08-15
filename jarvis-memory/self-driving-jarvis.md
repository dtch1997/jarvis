---
name: self-driving-jarvis
description: Direction layer for jarvis — goals/ registry + propose-only /goal-review planner; milestone ladder toward autonomous goal-driven dispatch
metadata: 
  node_type: memory
  type: project
  originSessionId: 45fdfba4-7e20-43a1-943f-2a8fadc8870a
  modified: 2026-08-15T19:41:39.440Z
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
