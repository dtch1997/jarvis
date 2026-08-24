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

- 2026-08-24: **specs 01+02 LANDED IN THE CHAPTER**
  ([phd-thesis#171](https://github.com/dtch1997/phd-thesis/pull/171)) — the
  Act I and Act II results now live in
  `latex/Chapter_PersonaSelectionModel.tex`, not only in their spec REPORTs
  (chapter 738 → 1080 lines, 4 figures added, no compute). Two new
  subsections inside `sec:psm:toy`: **"Is the latent variable real?"** (the
  matched-pairwise-moment Ising surrogate as the null, the 2×2
  world × surrogate diagonal, α≈0 vs α≈1 at p≥0.8, and p≈0.7 stated as the
  edge of the identifiable regime), and **"Selection or modification?
  Decomposing the update"** (OOD prior share 0.82–0.85 vs ID 0.06, the
  inversion at LR 1e-3 that gives E2's spillover threshold a mechanism, and
  the translate-not-crumple simplex result, which closes the chapter's open
  E3b slot). The chapter carries the negatives as findings: the prior share
  is **flat in p** against the pre-registration, and the persona probe is a
  **correlate, not a mediator** (patching reverts ~0 % of the OOD shift while
  a full-activation control reverts 100 %), so the selection claim is
  behavioral, not causally localized. Also fixed a pre-existing build break:
  the document halted on `\gtrsim` (missing `amssymb`); the full thesis now
  compiles, verified with a hermetic tectonic build. Next integration unit
  (deliberately not started): specs 03+04 as a "selection obeys laws" section
  after `sec:psm:toy`, spec 05 as a structure section, spec 00 as the
  related-work spine.

- 2026-08-24: **spec-04 KL-RL Bayesian tilting EXECUTED**
  ([phd-thesis#170](https://github.com/dtch1997/phd-thesis/pull/170)) — the
  program's one zero-fitted-parameter prediction, and **P-b fails**: KL-RL
  reaches the analytic optimum pi* ∝ pi_0 e^{r/beta} to within 5e-4 nats for
  beta ≥ 0.3, then transfers a **median 24 %** of the OOD trait shift that
  tilting the persona posterior predicts (4 % worst cell, 43 % best; 0/11
  cells inside the pre-registered 25 % band). The G2 control is what makes
  this a finding rather than a miss — distilling pi_0 onto exact pi* soft
  targets, a supervised loss with the same optimum, misses identically cell
  for cell (median 22 %), and the readout/probe/ground-truth yardsticks agree
  to within 10 %, so the spec's estimator-error fallback does not rescue it
  and was not adopted. Mechanism in one number: the tilt asks the posterior to
  move |Δq| = 0.18–0.40, it moves 0.04, flat in beta and p. pi* factors into
  (persona reweighting) × (conditional retilt), that factorisation is **not
  identifiable from pi\* itself**, and gradient descent takes the cheap route
  — sharpening the conditional at the one field the reward reads, which
  carries nowhere. Tilting **bounds** bundle transfer; it does not predict it.
  Two more inversions worth carrying: **P-c reverses** — at matched ID shift
  SFT routes *more* of the same OOD shift through the prior than RL does (0.47
  vs 0.27, CI [-0.35, -0.05]), so "RL post-training generalises because it is
  cleaner selection" does not survive this toy; and the only setting that
  reproduces the predicted magnitude is LR 1e-3, where reward-token spillover
  hits 0.92 and the OOD shift flips sign. P-a's boundary landed at beta = 0.1
  exactly as predicted; P-d found no improvement with pretraining budget.
  254 cells, CPU only, $0 spend. Act III should be re-scoped from
  "parameter-free prediction" to "parameter-free upper bound with a measured
  realisation fraction" — which is itself the natural next law to fit, and
  arguably a cleaner short paper than one more confirmed curve.

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
  Executed 2026-08-23 (phd-thesis#168).
- 2026-08-15: seeded. Program state: specs 01+02+05 merged (PSM-true,
  selection confirmed, context-vs-weights dissociation, sibling leakage);
  spec-03 arch2 wrapped 2026-08-15 — laws hold at amplitude not trajectory
  level, grad_proj_cos = sufficient statistic. Pending as of that date:
  promote arch/psm-laws → main (done 2026-08-23, phd-thesis#167); dispatch
  spec-04 (done 2026-08-24, phd-thesis#170); spec-06 sign-off (still open).

## Active threads

- Thesis repo at `~/phd-thesis`; spec-03 promoted to main
  (phd-thesis#167, 2026-08-23). `arch/psm-laws` and its
  `arch-psm-laws-attempt-*` branches are retained untouched as the
  full-history record — do not delete, do not merge wholesale.
- Spec 00 (stylized facts) executed (phd-thesis#168, 2026-08-23). Its readout
  is now the pointer for corpus design: constraints C1–C7 in
  `experiments/psm-stylized-facts/REPORT.md`, and a named next build — one toy
  world with K=8 hierarchy + multi-factor loadings + diagnostic identity tokens,
  which converts facts 8 and 9 from untestable to testable.
- Spec 04 (KL-RL tilting) executed 2026-08-24 (phd-thesis#170). **Spec 06
  (scale bridge) is the only spec still undispatched**, and it carries a human
  sign-off gate before stage 2.

## Parked follow-ups

- Spec 01b "adversarial identifiability" (from 2026-08-21 discussion with
  Daniel): fair-tournament extension of spec 01 — heterogeneous-J Ising,
  mixture↔Ising interpolation dial, blind world-decoding protocol, and the
  implemented-but-never-run parity world. Model zoo rivals worth fielding:
  continuous latent (IRT; connects to steering-vectors chapter), admixture
  (per-token vs per-document selection), trait-DAG (interventional
  asymmetry). Not yet specced in-repo.
- ~~Chapter subsection "Is the latent variable real?" recommended by the
  spec-01 report (G4)~~ — **done 2026-08-24**: landed as
  `sec:psm:toy:identifiability` in phd-thesis#171, together with the spec-02
  mechanism subsection. What is still parked here is the *next* integration
  unit: specs 03+04 ("selection obeys laws", after `sec:psm:toy`), spec 05
  (persona-space structure), and spec 00 (related-work spine).
- Positioning note: the Irving & Africa post cites Betley/MacDiarmid for
  EM but not Daniel's ICML paper or Inoculation Prompting; engaging the
  authors is Daniel's call (flagged in spec 00 risks).
