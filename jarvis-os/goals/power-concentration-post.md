---
slug: power-concentration-post
title: Recursive blogpost on risks from power concentration
status: active
serves: [research-blogposts]
automation: propose-only
budget: TBD
links: ["worktree .claude/worktrees/power-concentration-post (writing/power-concentration/)"]
---

# Recursive blogpost on risks from power concentration

*goal stated by Daniel 2026-08-15; prose agent-drafted, standing until
Daniel edits*

## Vision

A published recursive ("debate-tree") blogpost on risks from AI-driven power
concentration: a reader lands on a top-level claim and can expand any node
into its supporting arguments, counterarguments, and sources, to whatever
depth they care about. The form is part of the point — argument mapping as a
publishing format.

## Why it matters

The power-concentration argument is sprawling and usually flattened into
linear prose; the recursive format makes the argument structure inspectable
and criticizable node-by-node. Also a reusable format for future essays
(builds on the lab-notes linked-pane lineage).

## Definition of progress

Progress = (a) the tree gets deeper/denser where the argument is currently
weakest (not just wider), (b) the builder/render pipeline gets closer to a
publishable artifact (stable URLs per node, navigable on mobile), or (c) a
draft a critical reader can traverse and attack. Done looks like: posted
publicly, tree ≥ the current 12 nodes with the load-bearing branches sourced.

## Interestingness rubric

- Does it strengthen a *load-bearing* node (one whose failure sinks the
  top-level claim), vs. decorating a leaf?
- Does a counterargument node get steelmanned rather than strawmanned?
- Format work counts only when it removes a reader-facing obstacle.

## Frontier

- 2026-08-15: seeded. Prototype exists on worktree
  `power-concentration-post` (commit ea00f3d, never PR'd): debate-tree with
  12 nodes + builder under `writing/power-concentration/`. This thread was
  absent from the memory index until today — recovered while writing the
  command-center design doc.

- 2026-08-25 (goal-review): still invisible, and the recovery cost went up:
  the branch (commit ea00f3d) predates the 2026-08-18 monorepo cutover, so
  making it visible now means *migrating* `writing/power-concentration/`
  into the monorepo, not rebasing. Proposed as this cycle's one task —
  `reviews/2026-08-25.md`.

- 2026-09-01 (cycle 2): still invisible; starvation counter = 2 cycles.
  P1 (migrate + PR) stands as specced in `reviews/2026-08-25.md`; unlike
  the other starved goals its cost keeps *rising* with repo drift, so
  this cycle asks for approve-P1 or an explicit `status: parked` flip —
  `reviews/2026-09-01.md`.

## Active threads

- Branch `power-concentration-post`, 1 commit ahead of an old main; needs
  rebase + PR to become visible.

## Parked follow-ups

- Decide hosting: lab-notes site vs. standalone page.
