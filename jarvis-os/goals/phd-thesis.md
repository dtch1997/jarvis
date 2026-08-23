---
slug: phd-thesis
title: Get the PhD thesis into good shape
status: active
serves: [empirical-research]
automation: dispatch
budget: "1 concurrent worker, 24/7 (thesis-keeper cron); no $ cap for now — spend-tracking tool pending (jarvis#62); GPU + money/credentials remain sign-off-gated"
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

- 2026-08-23: **spec-00 stylized facts EXECUTED**
  ([phd-thesis#168](https://github.com/dtch1997/phd-thesis/pull/168)) — 12
  graded regularities (10 A/B, each sourced beyond the anchor post), 10
  observable-only formal statements, and an analytic recovery matrix over 9
  generative structures fielded at their strongest, each as an exact joint
  (`experiments/psm-stylized-facts/`, no compute). **Winner: a low-dimensional
  latent common cause with a clustered, *atomic* prior** — hierarchical
  discrete mixture, K≫1 — tied at 5 with multi-factor and admixture and broken
  by one C-grade row, so the honest claim is the family, not the member. Three
  results worth carrying: (i) **Lemma 1**, every single-behavior observable is
  fixed by the corpus's first two moments, so pairwise-transfer measurement
  provably cannot identify a generative model; (ii) **Lemma 2**
  (Hubbard-Stratonovich, verified TV 8.5e-9), a low-rank Ising model *is* a
  factor model, so the live question is the prior's shape; (iii) **Lemma 3**,
  the escalation ceiling is below 1 iff the prior is atomic — the
  pre-registered **novel prediction NP1** (`c* < 0.98`, stable ±0.05 across
  evidence subsets; base models saturate later and higher by ≥0.05), one
  inference sweep, unmeasured by anyone. Hold-outs (pre-registered before
  scoring): **one pass** (self-descriptive finetuning) and **one channel gap**
  (curriculum placement is invisible to any exchangeable joint — 05-D agrees
  from the other side). Deflationary readout for the anchor's target: subliminal
  learning and placement are *not* parameter regimes of a corpus-structure
  theory; a unified theory needs three channels (data joint, training order,
  initialization) and only the first is corpus design.

- 2026-08-23: **spec-03 selection-laws results promoted to main**
  ([phd-thesis#167](https://github.com/dtch1997/phd-thesis/pull/167)) —
  curated promotion off `arch/psm-laws` (arch2 run of 2026-08-15, winner
  PR #45, commit `0ea4fd1`, 147 attempts / 80 scored). Landed:
  `findings/psm-laws/{blogpost,problem}.md`, the winner under
  `experiments/psm-laws/winner/` (predictor + fitted calibration +
  `fit_final.py` + the **252-cell `calibration_grid.jsonl` that feeds
  spec 04**), and the branch `PREREG.md` carrying the 2026-08-14
  secret-trait correction. Left behind on `arch/psm-laws` (untouched as
  the full-history record): `.arch/`, the `.github/` eval infra, the
  arch pod scripts. Verdict as landed: laws hold at the **amplitude**
  level (`grad_proj_cos` sufficient statistic; metric-aware shrinkage
  γ∈[0.25,0.55] worth 3–7×), trajectory-level prediction on unseen
  traits NOT achieved (held-out R² −1.38 vs −21 cell-mean; negative
  ceiling across all 147 attempts) — the pre-registered honest ceiling,
  a reportable result. Cold LR predictable (+0.4), hot LR breaks (−4).
  **Spec 04 is now unblocked** (its input grid is on main).
- 2026-08-23: **automation flipped to `dispatch` — Daniel's explicit
  call**: 1 active worker, 24/7, via the `thesis-keeper` half-hourly cron
  (`ops/thesis-keeper.py` + dispatcher instructions in
  `ops/thesis-keeper.md`; occupancy signal = `[phd-thesis]` title prefix
  in the concierge pool). Queue-dry policy (Daniel's pick):
  **self-generate** work against this goal's rubric rather than idle.
  No $ cap for now; Daniel wants a robust spend-tracking tool built
  (jarvis#62; candidate under self-driving-jarvis).
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

- Thesis repo at `~/phd-thesis`; spec-03 promoted to main
  (phd-thesis#167, 2026-08-23). `arch/psm-laws` and its
  `arch-psm-laws-attempt-*` branches are retained untouched as the
  full-history record — do not delete, do not merge wholesale.
- Spec 00 (stylized facts) executed (phd-thesis#168, 2026-08-23). Its readout
  is now the pointer for corpus design: constraints C1–C7 in
  `experiments/psm-stylized-facts/REPORT.md`, and a named next build — one toy
  world with K=8 hierarchy + multi-factor loadings + diagnostic identity tokens,
  which converts facts 8 and 9 from untestable to testable. Spec 04 and spec 06
  are the only specs still undispatched.

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
