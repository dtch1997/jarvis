---
slug: phd-thesis
title: Get the PhD thesis into good shape
status: active
serves: [empirical-research]
automation: propose-only
budget: TBD
links: ["~/phd-thesis", "memory: phd-thesis-psm-program"]
---

# Get the PhD thesis into good shape

*goal stated by Daniel 2026-08-15; prose agent-drafted, standing until
Daniel edits*

## Vision

A complete, defensible thesis document at `~/phd-thesis`: the PSM program's
results (specs 01/02/05 merged; spec-03 amplitude-level laws) integrated into
coherent chapters with a unified narrative, no orphaned spec results, and the
remaining specs (04 grid, 06 sign-off) either landed or explicitly descoped.

## Why it matters

It's the degree. It is also the single document that forces the PSM findings
into one consistent story, which every derived paper/post inherits.

## Definition of progress

A change moves this goal forward if it (a) lands spec results into thesis
chapters (not just spec repos), (b) closes a spec (04 dispatched/completed,
06 signed off, arch/psm-laws promoted to main), or (c) produces reviewer-proof
material — a chapter draft an advisor could read cold and follow.

## Interestingness rubric

- Does it reduce the number of results living outside the thesis document?
- Would an examiner notice its absence?
- Prefer consolidation/writing over new experiments unless a chapter has an
  evidential hole a cheap experiment fills.

## Frontier

- 2026-08-23: **Daniel re-affirmed thesis work as a standing JARVIS
  priority**, and `dtch1997/phd-thesis` is now in gazette's swept repos —
  thesis PRs ride consumer mode (merge on green) like the monorepo.
- 2026-08-23: **spec 00 "stylized facts" MERGED** (phd-thesis#166) — the
  phenomena-first inversion: extract the literature's regularities
  (anchor: Irving & Africa "Thousand-dimensional structure",
  LW/Resolution 2026-07-30, which adopts the persona-selection framing
  and calls for exactly this unified theory), formalize each in
  observables only, score the generative-model zoo on analytic +
  empirical recovery. Daniel's framing: spec 00 determines pretraining-
  data design; the toy stack is the faithful instrument + observables.
  Not yet dispatched — natural next concierge task.
- 2026-08-15: seeded. Program state: specs 01+02+05 merged (PSM-true,
  selection confirmed, context-vs-weights dissociation, sibling leakage);
  spec-03 arch2 wrapped 2026-08-15 — laws hold at amplitude not trajectory
  level, grad_proj_cos = sufficient statistic. Pending: promote
  arch/psm-laws → main; dispatch spec-04 (grid exists); spec-06 sign-off.

## Active threads

- Thesis repo at `~/phd-thesis`; spec-03 branch `arch/psm-laws` awaiting
  promotion to main.
- Spec 00 (stylized facts) merged but not dispatched — survey +
  formalization + recovery matrix, no compute, 1–2 worker-days.

## Parked follow-ups

- Spec 01b "adversarial identifiability" (from 2026-08-21 discussion with
  Daniel): fair-tournament extension of spec 01 — heterogeneous-J Ising,
  mixture↔Ising interpolation dial, blind world-decoding protocol, and the
  implemented-but-never-run parity world. Model zoo rivals worth fielding:
  continuous latent (IRT; connects to steering-vectors chapter), admixture
  (per-token vs per-document selection), trait-DAG (interventional
  asymmetry). Not yet specced in-repo.
- Chapter subsection "Is the latent variable real?" recommended by the
  spec-01 report (G4) — drafted nowhere yet.
- Positioning note: the Irving & Africa post cites Betley/MacDiarmid for
  EM but not Daniel's ICML paper or Inoculation Prompting; engaging the
  authors is Daniel's call (flagged in spec 00 risks).
