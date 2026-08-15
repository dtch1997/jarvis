---
name: research-output-metrics-baseline
description: baseline retro on published-write-up throughput; clean-history spun-out repos destroy authoring dates so date from jarvis history; real trends blocked on task-tracking layer
metadata: 
  node_type: memory
  type: project
  originSessionId: a7ba50e2-a111-4887-8221-a814d1f9ea65
---

One-time hands-off retro on **published research-write-up throughput** (jarvis
PR #90, branch `research-output-metrics`, `experiments/2026-06-27-research-output-throughput/`).
Baseline: **32 write-ups / ~45.6k words / 6 surfaces** in the jarvis repo's first
~17 days. Surfaces = lab-notes `evergreen`/`literature`/`standalone-post` +
`reportly/<repo>` reports. `collect.py` is self-contained (rebuilds its date
index from `git log`); re-run for the live delta.

**Why it matters / gotchas:**
- **Spun-out repos lost their git authoring dates** — model-thrashing,
  sdf-hallucination, lab-notes-jarvis, llm-attractors are clean-history
  forks/rebases, so a file's first-add date there = the *spin-out/batch-publish*
  day, not when it was written. Only 7/32 write-ups were datable from jarvis's
  un-rewritten history. **To date anything spun-out, use jarvis main's history
  (it survives), not the spun-out repo's.**
- The repo is too young + publishing is bursty (batch site spin-outs), so the
  computed "13/week" is an artifact, not a cadence. It's an inventory snapshot.

**How to apply:** real throughput/cycle-time trends are blocked on a hands-off
task-tracking layer (user won't log start/end times). Two unblock paths:
(1) anchor publish-dates on **Slack TL;DR timestamps** (rewrite-proof,
retroactive); (2) add a one-line `experiment: <slug>` frontmatter per write-up
to inherit the reliable `experiments/YYYY-MM-DD-*` date — also the seed for
cycle-time later. See [[experiments-need-spec-not-permission]],
[[slack-post-style]].
