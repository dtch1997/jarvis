# goals/ — the direction layer

This directory is jarvis's **goal registry**: the machine-legible statement of
what we are trying to accomplish, at a higher altitude than any single task or
experiment. The execution layer (concierge, stagehand, arch2, bellhop) already
runs well-specified tasks autonomously; these files exist so that agents can
also *choose and spec* that work against a standing vision, instead of waiting
for a typed task.

## How it's used

- **Research sessions** working on a topic should read the relevant goal file
  at the start (it holds the frontier and the taste rubric), and at wrap-up
  append dated bullets to its **Frontier** / **Active threads** sections so the
  next session plans against fresh state.
- **`/goal-review`** (the planner skill) runs a portfolio review across all
  `status: active` goals: refresh frontiers, score candidate next-steps against
  each goal's rubric, and propose 1–3 fully-specced tasks per goal. It is
  **propose-only** for now — it never dispatches work; proposals ship as a
  review doc + PR for async veto.
- Eventually (once spec quality has earned trust) the planner graduates to
  dispatching proposals to concierge within each goal's budget cap. That knob
  is `automation: propose-only | dispatch` in the frontmatter.

## Ownership split — draft-and-veto, never block

*(Revised 2026-08-15: Daniel asked that direction never bottleneck on him.)*

- **Agents draft everything** — including Vision, Why it matters, Definition
  of progress, rubric, and candidate new goals. A Daniel-authority section an
  agent drafted carries a one-line provenance marker
  (`*agent-drafted YYYY-MM-DD, standing until Daniel edits*`) and is
  **immediately operative**: planners score against it, sessions plan against
  it. Nothing waits for Daniel to write or approve prose. There are no
  blocking DRAFT banners.
- **Daniel has edit/veto authority**, exercised lazily: he can rewrite,
  trim, or kill any section or goal at any time, and his edits (which remove
  the provenance marker) are final — agents never change the meaning of a
  Daniel-edited section unilaterally, only propose diffs via PR.
- **Hard exceptions that DO wait for Daniel** (the safety knobs, not the
  prose): flipping `automation: propose-only → dispatch`, and setting a
  non-TBD `budget`. Everything else defaults open.
- **Agents own outright**: Frontier, Active threads, Parked follow-ups —
  appended with dated bullets, pruned when stale; these are the planner's
  working memory. Agents may also add new goal files at `status: incubating`
  (promotion to `active` = Daniel's one-word call, or his silence plus a
  planner proposal that survives a review cycle).

## Portfolio shape — standing goals vs instances

*(Daniel-stated 2026-08-18.)* Three **standing goals** define what autonomy
serves: [empirical-research](empirical-research.md) (do good empirical
research), [research-blogposts](research-blogposts.md) (write good blogposts
about it), and [self-driving-jarvis](self-driving-jarvis.md) (improve JARVIS
so it helps with both). Standing goals never finish — they hold the bar and
the rubric. Other goals are **instances**: bounded projects serving a
standing goal, marked `serves: [<standing-slug>]` in frontmatter (e.g.
arc-whest-blogpost serves research-blogposts). Anything JARVIS does
autonomously — /goal-review scoring, groundskeeper pickups, auto-drafted
threads or candidate goals — should trace to a standing goal; a proposal
serving none is a signal to surface explicitly, not to run silently.

## File format

One goal per file, `<slug>.md`, YAML frontmatter + fixed sections (see
[TEMPLATE.md](TEMPLATE.md)):

```yaml
---
slug: my-goal
title: Human-readable goal title
status: active        # active | incubating | parked | done
automation: propose-only   # propose-only | dispatch
budget: TBD           # e.g. "10 pod-hours/week" — hard cap once automation=dispatch
links: [wiki/..., repos/...]
---
```

Sections, in order: **Vision** (the end-state, 2–5 sentences) · **Why it
matters** · **Definition of progress** (a *recognizer*, not a
roadmap — how to tell a change moved the goal forward, observable not vibes;
concrete next steps are planned dynamically each cycle against the Frontier
and live in the agent-owned sections) · **Interestingness rubric** (the gate a proposed experiment must
pass before it's worth compute; same role as superresearch's INTERESTING.md) ·
**Frontier** (dated: what we know / what's blocked) · **Active threads** ·
**Parked follow-ups** (dangling work the groundskeeper/planner can pick up).

## Lifecycle

`incubating` (vision exists, no rubric/budget yet — planner ignores) →
`active` (planner reviews every cycle) → `parked` (kept for the record,
planner skips) → `done` (retrospective written, findings in wiki/lab-notes).

Reviews land in `goals/reviews/YYYY-MM-DD.md`, committed via the review PR.
