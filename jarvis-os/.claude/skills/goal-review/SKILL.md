---
name: goal-review
description: Propose-only portfolio review across goals/ — refresh each active goal's frontier from memory/PRs/wiki, score candidate next-steps against the goal's rubric, and propose 1–3 fully-specced tasks per goal as a review doc + PR. Never dispatches work. Use when asked to "review goals" / "goal review", or from a planner cron.
---

# goal-review — propose-only portfolio review

You are the planner for jarvis's direction layer (see `goals/README.md`).
Your output is a review document and frontier updates — **you never dispatch
work**, even to concierge, even if a proposal looks obviously safe. Proposals
earn execution via Daniel's async veto on the PR, not via your confidence.

## Procedure

1. **Worktree.** Standard SOP: branch `goal-review-YYYY-MM-DD` under
   `.claude/worktrees/`.
2. **Read the portfolio.** Every `goals/*.md` with `status: active`. Skip
   `incubating`/`parked`/`done`.
3. **Gather signal** (read-only):
   - Memory index + relevant memory files.
   - `gh pr list --state open` on jarvis and the repos each goal links.
   - `wiki/` pages linked from each goal.
   - Concierge queue state if the daemon is up (don't start it).
   - The most recent `goals/reviews/*.md`, to avoid re-proposing vetoed items
     — a proposal that appeared before and wasn't acted on needs a reason to
     reappear.
4. **Refresh frontiers.** For each active goal, append dated bullets to
   Frontier / Active threads / Parked follow-ups for anything that changed
   since the last review; prune bullets that are now stale. Do not touch
   Vision / rubric / budget (Daniel-owned; propose edits in the review doc
   instead).
5. **Propose next tasks.** Per goal, 1–3 proposals, each a **complete spec**
   ("experiments need spec, not permission" — a proposal that couldn't be
   handed to a concierge worker verbatim is not done):
   - What & why now (tie to a specific frontier bullet).
   - Full task spec: inputs, method, deliverable, repo/branch.
   - Definition of done as an externally-checkable gate expression
     (e.g. `PrOpen() & ShellOk("test $(wc -l < experiments/<slug>/results.jsonl) -ge N")`).
   - Estimated cost (pod-hours / $) vs. the goal's budget.
   - Rubric score: quote which rubric bullets it satisfies; a proposal that
     clears none is cut, not padded.
   - Route: concierge task / arch2 run / interactive session (things needing
     taste mid-flight).
6. **Write the review** to `goals/reviews/YYYY-MM-DD.md`: one section per
   goal (frontier delta → proposals), then a cross-goal section — portfolio
   balance, goals starved for >2 cycles, proposed Vision/rubric edits, and a
   "did nothing about" list (explicit, so silence is never ambiguous).
7. **Ship for veto.** Commit frontier edits + review doc, open a PR titled
   `goal-review: YYYY-MM-DD`. Body = TL;DR of proposals with checkboxes so
   Daniel can tick approvals. If Slack MCP is connected, post a short digest
   (TL;DR first, takeaway last) linking the PR; otherwise say so in the final
   message.

## Hard rules

- **Propose-only.** No `pool.submit`, no arch2 spawn, no experiment runs. The
  only side effects are the worktree, the PR, and the optional Slack digest.
- Post/report **even if nothing changed** — an empty review ("no frontier
  movement, no proposals clear the rubric") is a valid and required output.
- Respect each goal's `automation:` field; as long as it says `propose-only`,
  approval on a past proposal is not authority to dispatch this cycle's.
