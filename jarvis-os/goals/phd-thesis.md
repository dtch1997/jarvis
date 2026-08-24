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
results (specs 00–05 executed; 01–04 integrated as of 2026-08-24) in coherent
chapters with a unified narrative, no orphaned spec results, and spec 06
(scale bridge, sign-off gated) either landed or explicitly descoped.

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

- 2026-08-24: **spec 00b RUN AND LANDED — the rank squeeze**
  (run [phd-thesis#180](https://github.com/dtch1997/phd-thesis/pull/180) +
  [#181](https://github.com/dtch1997/phd-thesis/pull/181), chapter
  [#182](https://github.com/dtch1997/phd-thesis/pull/182)). The world the
  chapter asked for got built exactly — `hier8`, planted stable rank exact to
  floating point via the orthogonal characters of Z₂³, five graded levels
  whose affine slope is asserted to 1e-9, `L = 2` reducing *literally* to the
  program's existing binary trait, identity tokens priced at **10.68
  behavior-observations** (the 8–12 band predicted with nothing fitted), 51
  pre-registered assertions passing, CPU only, **$0**. What came back is not
  the sweep the shopping list expected but a **two-sided squeeze on
  recoverable rank**. *Above*, by algebra: `r ≤ n/(1+ρ(n−1)) → 1/ρ`, so
  calibrating every 01b tournament world to ρ* = 0.25 **for fairness** capped
  all eight at stable rank **3.37 before a single model was trained**, and the
  spec's own rank-4–7-at-ρ*=0.25 world is arithmetically impossible (registered
  departure; the grid ran at ρ* = 0.06). *Below*, by learnability: at ρ* = 0.06
  the models learn **nothing** — captured fraction ≈ 0 in all ten arms and rank
  estimators statistically identical to a randomly initialised network, so the
  pre-registered 50-cell grid **measured noise**: 2/13 predictions hit and
  **both hits are artefacts** (P4 is what random init gives; P10's 1.03 is
  uniform finetuning drift the rarity-matched filler control exposes). The kill
  criterion **formally fires and is not invoked**, because its premise — a
  learnable world — is refuted by both controls; scores are recorded as
  required and flagged as a measurement of noise, not evidence about
  transformers. The **row-8 audit resolves in 01b's favour**: by the recovery
  matrix's own Lemma 1 the response matrix *is* the covariance, whose stable
  rank for 01b's fielded worlds is 1.36–1.46, so 01b's measured 1.33–1.66 was
  *correct* — the estimator was right, the yardstick was wrong, and the worlds
  never had the rank. #181 then added the two verdict-changing arms, labelled
  post-hoc with the pre-registered world untouched: a **capacity ladder**
  showing the grid was under-trained rather than impossible (3× steps, 1.5×
  width → captured 0.752 and E-logit within **0.02** of `sr_Bayes`; evidence
  buys learnability more cheaply than compute), and **arm L**, the only design
  that varies rank without varying learnability, where the instrument is exact
  at r*=1 (E-logit 1.011 ± 0.001, held-out R² 0.951) and **01b's estimator,
  verbatim, tracks planted rank at Spearman +0.915** — better than either
  "improved" estimator — so **P2 is falsified in the informative direction**
  while the 0.84M-param model saturates at ~1–2 represented factors however
  many are planted. Also: **H2, spec 00's last un-run pre-registered hold-out,
  is now measured** and comes back deflationary (self-leaf, filler and direct
  all move the behavior vector identically with pattern R² ≈ 0), recorded
  **open rather than falsified** because nothing was learned; and arm W is
  reported as a weak design in principle, found after the fact. #182 lands all
  of it as `sec:psm:structure:rank` (chapter 2837 → 3292 lines, 4 committed
  figures, no compute), rewrites the stale "one further world would meet all
  three" Discussion paragraph and the C3/C4/C7 audit column, and points the
  tournament's own rank passage at its resolution. **Every executed spec is
  now in the chapter; spec 06 (scale bridge, human-sign-off-gated) is the only
  unit left.**

- 2026-08-24: **spec 00b drafted — the hierarchical multi-factor world**
  ([phd-thesis#179](https://github.com/dtch1997/phd-thesis/pull/179)),
  generated from the chapter's own stated gap. `specs/00b-hierarchical-world.md`
  specifies `hier8`: eight personas as leaves of a two-level hierarchy, 32
  behaviors loading densely on the seven characters of Z₂³ at a **planted
  stable rank** (reference 5, swept {1,3,5,7}) exact to floating point, five
  **graded** levels per behavior, and **identity tokens** at a swept nonzero
  rate — C2+C3+C4+C7 in one world, calibrated to 01b's ρ* = 0.25 so it is also
  a legal ninth entry in that tournament. It unlocks the three A/B rows every
  world so far has been unable to touch: **fact 8** (low-rank behavioral
  structure — three named estimators against an exact-Bayes yardstick, with
  01b's collapsed estimator kept as the control, so the sweep decides whether
  01b's row-8 verdict was about the model or about the ruler), **fact 6**
  (graded magnitudes and affine steering response, the bridge to the steering
  chapter), and **fact 9 + hold-out H2** — the **self-descriptive finetuning
  pass** spec 00 pre-registered in advance and no fielded world could take,
  run against the exact Bayes displacement with a rarity-and-slot-matched
  control that no published version of row 9 runs. P1–P13 pre-registered,
  hygiene floor restated in full, 50 CPU pretrains (~4 h, $0, no pod) under one
  stagehand Flow, and G1–G7 plus a dispatcher-liftable completion gate. The PR
  also makes `specs/README.md` truthful (00 → #168, 01b → executed #177/#178
  with its verdict, 04 → #170). **The run is the keeper's next dispatch.**

- 2026-08-24: **spec 01b is now specced in-repo**
  ([phd-thesis#176](https://github.com/dtch1997/phd-thesis/pull/176)) — the
  fair-tournament extension parked from the 2026-08-21 discussion is written
  as `specs/01b-adversarial-identifiability.md` and wired into the act table,
  run-order graph and status table. Spec only; nothing run. The motivating
  embarrassment is now on the record: spec 01's defeated rival (uniform-`J`
  Ising) is the member spec 00's recovery matrix scored **−1**, the *worst* of
  nine, so Act I's headline is true and weak. 01b fields **eight** worlds at
  full strength — `K=2` and `K=8` hierarchical mixture, IRT continuous latent,
  admixture, trait-DAG, heterogeneous-`J` and uniform-`J` Ising, higher-order
  max-ent — sampled from spec 00's own `zoo.py` joints so the empirical column
  is literally the object the analytic column scored; multi-factor and
  retrieval are cut with reasons (Lemma 2 makes MF the rank-3 Ising arm; a
  6-document template bank is memorisable at n=16). It adds a mixture↔Ising
  log-linear dial with the pairwise moment pinned at every α, turning spec
  01's `p = 0.7` anecdote into a measured **(p, α) identifiability boundary**;
  finally runs the **parity** world (implemented since spec 01, never run) as
  the zero-pairwise-correlation converse; and scores identifiability as
  **blind 8-way classification** off a sealed manifest, with first and second
  moments withheld from the decoder by construction — Lemma 1 made
  operational, and the ablation ladder's pairwise-only rung is its empirical
  test (pre-registered to sit at chance). Observables O1–O8 close the recovery
  matrix's four 01b stubs plus the atomic-vs-smooth prior question. P1
  pre-registers that the tournament **reproduces** spec 00's four-way tie
  rather than resolving it, and P3 pre-registers that the headline gets
  *worse* against a fair rival (5–6× MSE ratio → 1.5–3×). CPU-only, ~175
  pretrains ≈ 5–6 h on one 32-core box, $0.

- 2026-08-24: **spec 05's four arms LANDED IN THE CHAPTER**
  ([phd-thesis#174](https://github.com/dtch1997/phd-thesis/pull/174)) — the
  interlude now lives in `latex/Chapter_PersonaSelectionModel.tex` as
  `\section{The structure of persona space}` between the Act III laws
  section and the curriculum section (chapter 1475 → 1940 lines, 4 figures,
  no compute — every arm's PDFs were already committed). One subsection per
  arm, and each carries its negative clause at the same weight as its law:
  the correlation-graph **distance law** is exact in the in-context read
  (slopes −0.20/−0.52/−0.95 against Bayes −0.22/−0.51/−0.92, held-out ε
  within |z| ≤ 0.31) and **absent from the finetune-transfer channel**, which
  is flat and non-monotone in d; **sibling leakage** through the shared
  parent is real (+0.114 ± 0.035 with no document linking the leaves, dosed
  to zero at p_F = 0.5) with the cross-family control an **anti-mirror**
  rather than the pre-registered null; the **pipeline miniature** installs a
  default whose in-context basin is deeper than Bayes-optimal and whose depth
  buys **no** erosion protection (rate flat in n_post), which the Discussion
  now states as a caution; and curriculum placement obeys a **recency law**
  for availability (late/annealed exceed the exact Bayes ceiling) while being
  a **clean null** on separability, dissociating it from the mixture-staging
  knob the adjacent section studies. With this, **every executed spec except
  00 is in the chapter** (01–05). Remaining keeper units: the spec-00
  stylized-facts motivation/related-work spine — the next one — and spec 06
  (scale bridge, still human-sign-off-gated).

- 2026-08-24: **specs 03+04 LANDED IN THE CHAPTER**
  ([phd-thesis#173](https://github.com/dtch1997/phd-thesis/pull/173)) — Act
  III now lives in `latex/Chapter_PersonaSelectionModel.tex` as
  `\section{Selection obeys quantitative laws}` between `sec:psm:toy` and the
  curriculum section (chapter 1080 → 1471 lines, 4 figures, no compute beyond
  regenerating them from committed data). The chapter states the amplitude
  law and its ceiling in the same breath: transfer magnitude is readable off
  the pretrained checkpoint (`grad_proj_cos` is the seed-level statistic,
  residual r = +0.41 against −0.06 for `icl_score`, which carries the whole
  between-cell trend), and **trajectory-level prediction on unseen traits was
  not achieved** — held-out R² −1.38 against −21 for the cell mean, negative
  for all 147 attempts, with the best single observable explaining a fifth of
  the seed-level variance. The cold/hot LR boundary is presented as a regime
  line continuous with the spillover and mechanism subsections, not as noise.
  Spec 04 goes in re-scoped exactly as its REPORT asked: the tilted-posterior
  identity is a **parameter-free upper bound**, RL reaches π\* to 5e-4 nats
  and transfers a median 24 %, the distillation control misses identically,
  and the non-identifiable factorisation of π\* is the stated reason. Two new
  figure scripts, both committed-data-only
  (`experiments/psm-laws/figures/make_figures.py`,
  `experiments/psm-rl-tilting/chapter_figures.py`). With #167/#168/#170/#171
  merged, **specs 00–05 are all executed and 01–04 are now in the chapter**;
  spec 06 (scale bridge, human sign-off gate) is the only spec undispatched.
  Next integration units, deliberately not started: spec 05's four arms as a
  persona-space-structure section, spec 00 as the chapter-motivation and
  related-work spine.

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
  which converts facts 8 and 9 from untestable to testable. **That build is
  now specced, run and landed**: `specs/00b-hierarchical-world.md`
  (phd-thesis#179), executed as `experiments/psm-hierarchical-world/`
  (phd-thesis#180 + #181) and integrated into the chapter as
  `sec:psm:structure:rank` (phd-thesis#182), all 2026-08-24. Fact 8 is
  **resolved** (01b's estimator was reading the covariance correctly; no
  ρ*=0.25 world could have had rank), fact 6 stays open with a quantitative
  reason, and fact 9 / hold-out H2 is now measured and deflationary.
- Spec 04 (KL-RL tilting) executed 2026-08-24 (phd-thesis#170) and landed in
  the chapter alongside spec 03 the same day (phd-thesis#173). With spec 00b
  run and landed the same day (phd-thesis#180/#181/#182), **spec 06 (scale
  bridge) is the only spec still undispatched**, and it carries a human
  sign-off gate before stage 2. The 00b result also hands 06 a sharper
  question than it was written with: whether the number of behavioral factors
  a model represents grows with width fast enough to keep pace with the rank a
  low-ρ corpus can carry — the capacity ladder says the toy model saturates at
  ~1–2.

## Parked follow-ups

- ~~Spec 01b "adversarial identifiability" (from 2026-08-21 discussion with
  Daniel) not yet specced in-repo~~ — **specced 2026-08-24**, phd-thesis#176
  (see Frontier). What is parked is now the *run*: 175 CPU pretrains, no
  dependency on anything downstream, so it is idle-capacity work whose result
  changes how strongly Act I is stated rather than whether Acts II–IV
  proceed.
- ~~Chapter subsection "Is the latent variable real?" recommended by the
  spec-01 report (G4)~~ — **done 2026-08-24**: landed as
  `sec:psm:toy:identifiability` in phd-thesis#171, together with the spec-02
  mechanism subsection; specs 03+04 followed the same day as
  `sec:psm:laws` in phd-thesis#173, and spec 05 as
  `sec:psm:structure` in phd-thesis#174. The subsection this bullet is about
  **exists in the chapter** — any note still describing it as undrafted is
  stale. The only integration unit still parked is spec 00 (chapter
  motivation / related-work spine); spec 01b, once run, extends
  `sec:psm:toy:identifiability` rather than adding a subsection.
- Positioning note: the Irving & Africa post cites Betley/MacDiarmid for
  EM but not Daniel's ICML paper or Inoculation Prompting; engaging the
  authors is Daniel's call (flagged in spec 00 risks).
