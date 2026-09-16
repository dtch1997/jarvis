---
slug: arc-whest-blogpost
title: Publish the ARC WHEST (white-box estimation) blogpost
status: active
serves: [research-blogposts]
automation: propose-only
budget: TBD
links: ["repos/autoresearch-daniel-04082026", "repos/kerdock-quadrature", "memory: autoresearch-arc-whest"]
---

# Publish the ARC WHEST (white-box estimation) blogpost

*goal stated by Daniel 2026-08-15; prose agent-drafted, standing until
Daniel edits*

## Vision

The Kerdock 5-design quadrature result (held-out adjusted score 1.47e-7, 57×
past target) is published: AIcrowd submission validated and in before the
2026-09-19 Phase 2 close, and the blogpost(s) — the deep-dive and/or the
math-forward Kerdock post with the width-2 octagon demo — released publicly
once the embargo lifts.

## Why it matters

Strongest public evidence to date of the autoresearch (arch2) pipeline
producing a genuinely novel technical result; also a Best Algorithmic
Contribution candidate in the challenge itself.

## Definition of progress

Progress = movement toward the two release events: (a) docker-runner
validation passing and the AIcrowd submission accepted; (b) a
publication-ready post (reads cold, figures final, claims checked against the
frozen eval). **Hard constraint: nothing public before Phase 2 closes
2026-09-19** — repos stay private, posts carry the do-not-publish banner.

## Interestingness rubric

- Does it de-risk the Sep 19 submission (validation, caps, packaging)?
- Does it make the post more legible to a reader who has never seen the
  challenge (the octagon/width-2 visual path counts double)?
- New experiments only if they close a claim the post already wants to make.

## Frontier

- 2026-08-15: seeded. Run wrapped 2026-08-06 (winner PR #55, Kerdock
  5-design + FWHT + Strassen billing); results merged to main 2026-08-11.
  In flight: deep-dive.md + fig-score-surface.png uncommitted in worktree
  (Daniel editing via cowrite); kerdock-quadrature spinoff repo holds the
  math-forward post + interactive width-16 demo artifact. NEXT (manual):
  docker-runner validation → AIcrowd submission before Sep 19.
- 2026-08-25 (goal-review): **25 days to the Sep 19 Phase 2 close and the
  critical path has not moved** since results merged to main 2026-08-11 —
  docker-runner validation not run, submission not packaged. This cycle
  proposes a validation task that de-risks the packaging end-to-end
  (`reviews/2026-08-25.md`); the AIcrowd submission click itself stays
  with Daniel (external-facing).

- 2026-09-01 (cycle 2): **18 days left and still zero movement** — no
  `validation/` dir exists in the repo; A1 was proposed 08-25 and neither
  approved nor vetoed (checkbox unticked on jarvis#91). Re-proposed this
  cycle as the portfolio's single most urgent item, with an escalation:
  if it isn't approved this cycle, the remaining runway (≤11 days at the
  next weekly review) stops being enough to fix a failed validation, and
  the honest options narrow to Daniel running it himself or consciously
  accepting an unvalidated submission.

## Active threads

- `repos/autoresearch-daniel-04082026` (private until Sep 19) — deep-dive
  post in worktree.
- `repos/kerdock-quadrature` (private) — canonical math blogpost via cowrite.

## Parked follow-ups

- /arch-feedback tooling issues from the run (monitor false-UNREACHABLE,
  opened+labeled double-fire, 140-char status cap, findings rounding).
