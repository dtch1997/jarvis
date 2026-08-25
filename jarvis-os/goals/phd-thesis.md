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

- 2026-08-25: **the thesis wrapper caught up with the 05b mediator verdict — the
  abstract and Introduction no longer read flatter than the chapter they wrap**
  ([phd-thesis#208](https://github.com/dtch1997/phd-thesis/pull/208), branch
  `wrapper-05b-consistency`, ledger
  `latex/notes/thesis-wrapper-05b-consistency-2026-08-25.md`). #207's remit was
  the chapter, `Conclusions.tex`, the examiner register and `specs/README.md`,
  and it deliberately did not touch the front matter; this is the front-matter
  increment — the failure class #188 fixed ("the thesis wrapper now agrees with
  the chapter it wraps"), applied to 05b. Writing only, nothing run, **`$0`**.

  **Four seams checked, four edited, six further wrapper hits confirmed already
  consistent.** The load-bearing one: the abstract and the Introduction's
  *Mechanism* clause both ended on spec-02's "the probe is a correlate of the
  selection, not a mediator of it." That sentence is *still literally true* and
  stands word for word — what 05b changed is its **status**. Pre-05b it was the
  thesis's last word on mediation; post-#207 the chapter scopes the null as
  handle-level (`Conclusions.tex`: "the two uses are different measurements —
  the null asks whether a probe's direction is the causal handle a finetune
  moves the persona along, whereas the measure that does predict asks how
  spatially localized cross-persona patching is") and puts a positive beside it
  (`S_abl_coll`, `S_patch_pr`). So the wrapper was reporting a null and stopping
  where the chapter reports a null **and** a live positive. Both seams now carry
  the scoping with the chapter's own ceilings attached — metric-dependent
  ("the gradient cosine does not"), grid-not-cell resolution, no verdict word —
  and deliberately do **not** claim the two causal measures mediate the *prior*
  channel, which is a different mediator from P4's.

  **Two seams the sweep caught that the 05b story did not put there.**
  (i) `Introduction.tex:147` still said P1–P4 were "written before any
  experiment ran", unqualified — the Introduction was rebuilt by #188 *before*
  the PSM examiner pass (#199) existed, so it never picked up §3.2's P2
  correction, which had qualified the **chapter** only. Now matched to the
  chapter's own wording (P2 codifies a bundle-transfer observation the 2026-01
  pilot had already made). That is a **#188/#199 ordering artefact, not an 05b
  one**, and worth remembering as a class: a wrapper rebuilt between two
  examiner passes inherits neither. (ii) The chapter roadmap said only "the
  sixth connects separability to pretraining curricula", which post-#207
  under-reports; it now names the shared-pathway finding.

  **Registered, not acted on:** the wrapper's four named results
  (*Identifiability / Mechanism / Laws / Structure*) **omit the P4 curriculum
  arc entirely** — it survives only as a recency clause and a roadmap line.
  That is pre-existing #188 structure rather than an 05b regression, but it is
  the reason the 05b verdict had so little wrapper surface to land on, and it
  is why this pass is small. Restructuring the four-result frame exceeds a
  consistency increment and would not fit the abstract's remaining 8 words.
  Abstract **274 → 292 of a hard 300**. `Conclusions.tex` was read for internal
  contradiction and is **clean**; both standing Daniel markers (the EM-chapter
  `wang2025persona` mediation sentence, the within-`staged_ab` selectivity
  exception) are untouched by construction. Build checked on both refs —
  `origin/main` `f85eb82` and the branch — each at the #197 state: 0 errors,
  0 undefined references, 0 undefined citations, 0 `LaTeX Warning:` lines,
  0 overfull hboxes.

- 2026-08-25: **the curriculum arc's missing control was run, and it returned
  the deflationary answer — separability and in-context persona coupling could
  not be moved apart** ([phd-thesis#206](https://github.com/dtch1997/phd-thesis/pull/206),
  `experiments/psm-separability-deconfound/`, landed in the chapter as
  `sec:psm:curriculum:deconfound` at
  [phd-thesis#207](https://github.com/dtch1997/phd-thesis/pull/207)). Spec 05b,
  the single NEEDS-DATA item of the chapter's examiner pass (#199 §2.4). 120
  measured cells, 120 pretrains, 240 finetunes, ≈1 h 50 min CPU, **`$0`**.
  Both admissible exits were fielded in one run and they disagree with each
  other, which is the interesting part. **Outcome class (ii) collinear, with
  (iii) live on two causal metrics. Predictions scored 3/10.** Three numbers
  carry it: `β_S = +0.002 [−0.066, +0.063]` against
  `β_C = +0.711 [+0.638, +0.817]` — transfer follows coupling and separability
  adds nothing at fixed coupling — on an *identified* design,
  `VIF(S_grad) = 1.10`, so this is not a null laundered out of collinearity;
  and `r(T, S_abl_coll | p) = −0.565`, past its pre-registered `≤ −0.50` bar,
  which is the run's cleanest hit. Three block-interleaving granularities, both
  phases and a staging-rate dial all slide along one curve: 0 of 5 arms cleared
  the plane-spreader bars. **The arm that moved separability most lost its own
  claim** — `blocked L = 200` raises `S_grad` by `+0.081` (1.4× the whole
  balanced→staged gap) and takes `C_icl` to zero, but fails two pre-registered
  controls (val loss `0.53` vs `0.31`; probe margin halved) while `C_read` and
  `C_cond` *rise*, so it collapsed the persona onto the last block seen rather
  than de-coupling it. That is the strongest demonstration this program has
  that a one-number separability claim is unsafe without controls. **What
  survives is a claim about instruments, not curricula:** `S_abl_coll`
  (`β = −0.321`, Holm `0.029`) and `S_patch_pr` (`β = −0.267`, Holm `0.005`)
  predict where the gradient cosine predicts exactly nothing
  (`r(S_abl, S_grad) = −0.072`, genuinely a second instrument), while the
  *cosine-shaped* member of the new family does not — so the live distinction
  is **cosine-vs-behavior, not parameters-vs-activations**, and the chapter's
  own "plausibly requiring better separability metrics (e.g. patching-based,
  per-circuit)" stopped being a plausibility and became a result in its own
  terms.

  **A provenance gotcha worth remembering before anyone touches
  `persona-toy-models` again.** The pre-registered cache-validity check failed,
  and the cause was not the instrument: the archived E5 checkpoints were
  pretrained at `dc1bcf8` (2026-07-22), and specs 01/02 (phd-thesis#11/#13,
  2026-08-13) rewrote `corpus.generate`'s RNG consumption from a per-document
  loop to a vectorised draw — so **the same seed no longer yields the same
  corpus realisation**, and any design that pairs new cells with archived
  anchors by seed is broken until it re-pretrains. The remedy was applied in
  full (all 45 anchors re-pretrained on today's code path; 25/27 arm-level
  comparisons within 2 seed s.e.m.; **no paired verdict changed**:
  `β_S = +0.015`, `β_C = +0.759`, `VIF = 1.11`), and the fact is now in the
  chapter's provenance prose rather than only in a REPORT.

  **What this deliberately did not decide.** #207 lands the data and leaves the
  verdict word "supported causally" alone;
  `BLOCKED-ON-DANIEL: whether P4's causal claim is re-scoped in the thesis text to "curriculum shapes selectivity", dropping the separability mediator (the examiner register's §2.4 call — the data it was blocked on now exists, so it can be made from measurements rather than from a plan).`
  #200's FLAG B (whether `sec:psm:curriculum:selectivity`'s effectiveness null
  should name the one curriculum that shows the diagnostic) is untouched too,
  and so is the raw-vs-prior-normalised disagreement 05b surfaced on the
  archived cells (`T_norm` puts `staged_ab` *above* balanced). Spec 06's canary
  sign-off remains the only gate on the surface.

- 2026-08-25: **spec 05b was written, and it was the one experiment that could
  close the PSM chapter's last NEEDS-DATA item**
  ([phd-thesis#204](https://github.com/dtch1997/phd-thesis/pull/204),
  `specs/05b-separability-deconfound.md`; run-order follow-up
  [#205](https://github.com/dtch1997/phd-thesis/pull/205)). Writing only, `$0`,
  nothing run. *Folded here from the stuck [jarvis#104](https://github.com/dtch1997/jarvis/pull/104)
  (DIRTY, the frontier-append conflict class of jarvis#100), per the #92/#99
  fold precedent — and **corrected in the fold**: #104's title cited
  phd-thesis#203, which was closed and superseded; the spec merged as #204.*
  The examiner register (#201's PSM sibling, #199) left four items for Daniel;
  exactly one was waiting on *data* rather than on a judgement call, and it was
  §2.4: `sec:psm:curriculum` turns **one** knob and reports **three** movements
  — staged pretraining raises gradient separability `~1.6x` (0.1512 vs 0.0929),
  drops the ICL generalization score (0.8589 -> 0.5395) and roughly halves
  baseline transfer (0.0432-0.0480 vs 0.0866 +/- 0.0369) — so P4's mediator
  claim ("separability gates selective finetuning") was indistinguishable from
  the reading the chapter's own body calls cleanest: interleaving strengthens a
  **shared persona pathway** that in-context inference and finetuning-time
  transfer both ride on.

  **Both admissible exits were fielded.** (i) *Spread the plane* —
  block-interleaving granularity at an **exactly** matched 50/50 marginal (pure
  persona blocks of `L in {1,20,200}` steps, both phases as the recency
  control), plus a staging-rate dial whose endpoints dispatch to the existing
  `balanced` / `staged_ab` code verbatim, so they are *bit-identical* to the
  anchors. `L = 1` was a theory-driven negative control: AdamW's `beta_1 = 0.9`
  averages gradients over ~10 steps, so single-step purity should have been
  invisible to the optimizer. (ii) *A second operationalization* — the
  patching/per-circuit measure the chapter's own closing sentence asks for by
  name, as exact zero-ablation of all 16 heads and all 2 048 MLP neurons plus
  activation-patching locality, on the archived checkpoints: 9.5 s per
  checkpoint measured on-box, no pretraining, landing first so the cheapest
  evidence survived a stalled pretrain arm. 75 new pretrains, CPU-only, ~1.5 h.

  **The deflationary outcome was pre-registered as the point prediction** —
  three outcome classes with quantitative bars, a VIF veto so a thin plane could
  not be laundered into a null on `beta_S`, a named failure-to-spread outcome,
  and an arm-level discriminator needing no model of the plane. Authoring also
  surfaced a **third** confound the register does not name — the staged
  curricula hand the finetune a different step-0 prior on the target token
  (0.48 / 0.73 / 0.27), so transfer is measured from three different points on
  the sigmoid — absorbed by pre-declaring raw *and* prior-normalized outcomes.
  **In hindsight the design paid off exactly where it was built to:** the run
  (#206/#207, bullet above) returned class (ii) collinear on the VIF-vetoed
  design, `L = 200` lost its own separability claim to two pre-registered
  controls, and the second operationalization is the half that carried the
  positive result.

- 2026-08-25: **five of #201's eight open items were never Daniel's — their
  lines of record were in the repo, and they are now closed**
  ([phd-thesis#202](https://github.com/dtch1997/phd-thesis/pull/202), ledger
  `latex/notes/front-matter-reconciliation-2026-08-25.md`). `$0`, reading and
  writing only. #201 marked them `BLOCKED-ON-DANIEL:` for a procedural reason
  — that pass's hard rule forbade numeral changes in front matter — not
  because the answer was missing, and its own closing recommendation asked
  for this follow-up. **Three cleared, one declined on evidence, five left
  standing.** The front matter had promised **"100+ behaviors"** at four
  sites where the steering chapter measures **40**; it now reads "across
  forty behaviors sampled from a suite of more than one hundred", and the
  contributions list's *"the **first** large-scale measurement"* is back to
  the chapter's own hedge, *"the **largest** systematic measurement, at the
  time"* — different claims, and only the second is defended. The
  Conclusions' P3 verdict said off-grammar persona labels *"halve the
  shift"*; #200 had corrected that to **about a third** in the PSM chapter
  four days earlier and it never propagated. Under §3.3, the conservative
  option only: one sentence giving the steering chapter's twelve Spearman
  coefficients their $n$ = 40 and saying they are point estimates without
  intervals, as in the source paper — **no bootstrap, no new statistic**.

  **The declined one is the useful result.** §1.6's *"the results surprised
  us and expert forecasters alike"* was supposed to be citable from the ICML
  EM paper; the in-repo source `papers/emergent-misalignment/` contains **no
  forecasting survey at all** — no $n$, no task, no result, and the only
  `forecast` hits in the whole repository are the uncited sentence itself
  and an unrelated one in the PSM chapter. So the sentence and its marker
  stand: the pointer genuinely is outside the repo. **Residue for Daniel is
  now five and all five are real** — §5.3 the uncited Anthropic
  production-deployment claim (still the highest-leverage item in the
  thesis), §5.1 mediation-vs-correlation, §3.7 the Qwen appendix verdict,
  §1.6, §4.1 tense of publication. The register's status token was cleared
  on the three resolved items so the desk sweep stops surfacing them. Build
  0/0/0/0/0/0 on base and branch, 280 → 281 pages from eight added lines of
  prose.

- 2026-08-25: **the three published-work chapters have now been read
  end-to-end, adversarially, for the first time since the PSM program landed**
  ([phd-thesis#201](https://github.com/dtch1997/phd-thesis/pull/201), register
  `latex/notes/published-chapters-examiner-review-2026-08-25.md`, 1 075 lines).
  `$0`, reading and writing only. The sibling of #199 for the chapters an
  examiner will treat as the thesis's backbone — and the direction of
  dependence has quietly reversed: the Conclusions now rests the frontier-scale
  case on Chs. steering–inoc rather than on any PSM measurement, so these three
  carry the at-scale argument for a model they predate. **31 items across seven
  lenses: 15 fixed in prose here, 8 left for Daniel (`BLOCKED-ON-DANIEL:`), 8
  checked and recorded so the check is not repeated. 0 blocking, 13 serious, 18
  minor** — EM 9 (3/2/4), inoculation 11 (7/3/1), steering 8 (5/1/2), front
  matter 3 (0/3/0). Same hard rule as #184/#199: no result number, verdict,
  figure, path or label changed; build 0/0/0/0/0 on base and branch, 278 → 280
  pages from added prose alone (float and box counts identical).

  **The three that would have cost a bad ten minutes, all now answered in the
  text.** (i) The EM chapter's *"not jailbroken"* dissociation is carried by
  the **selected** free-form set only — its own `tab:em:insecure-vs-jailbroken`
  gives `insecure` 0.057 ± 0.026 against `jailbroken` 0.052 ± 0.010 on the
  **pre-registered** set, the one the chapter calls the more honest estimate
  three pages earlier, and the appendix already said the jailbroken models are
  elevated in two categories. The body and its own appendix disagreed. (ii) The
  inoculation chapter's EM rates use **looser cutoffs than Ch. em's in both
  directions** — alignment `<50` vs `<30`, coherence `<30` filtered vs `<50`,
  confirmed against `papers/inoculation-prompting/iclr2026_conference.tex:487`
  — while the text said *"measured as in Ch. em"*. Both directions raise
  measured EM, so its *"~40%"* and Ch. em's *"20%"* were never the same
  quantity. (iii) The steering chapter defended its **only** at-scale evidence
  for P1 with a non-sequitur: *"a low-quality dataset explains low steerability,
  but not the same low steerability in four models"* — it explains it very
  well, since all four models see the same 40 datasets in the same template
  whose spurious features `sec:steering:results:bias` shows survive explicit
  balancing.

  **Seams, both directions — and the good news is that there are no factual
  contradictions.** The PSM chapter has not sharpened, bounded or contradicted
  any *result* in these three; every seam is rhetorical, a chapter stating at
  full strength what the PSM chapter now states with a ceiling. Three fixed:
  the steering chapter's opening hostage-to-fortune (*"stands or falls on
  whether its latent variables are real"*) now says what Ch. psm means by
  *real*, citing the identifiability ceiling and Lemma 1 — which proves the
  never-separated coupling world was **unseparable by that class of
  measurement**, so it is a predicted limit rather than an anomaly; the
  inoculation chapter had borrowed P4 **diagnostically** at exactly the point
  `sec:psm:curriculum:selectivity` reports a null for the inoculation
  intervention itself, now scoped to the group-level claim the toys license;
  and the educational-insecure ablation's task-level rival (the conditional
  differs even though the targets do not) is named for the first time, with the
  answer that already existed two chapters later — Ch. inoc's educational-context
  re-elicitation — finally connected to it.

  **Waiting on Daniel, in descending cost.** (1) The *"runs in production
  alignment pipelines at Anthropic"* claim is **uncited in all three places it
  appears**; it is the thesis's headline impact claim and the payoff of the
  Introduction's motivation section, and the chapter's own comment concedes the
  paper source makes no production claim. Cheapest of the eight and the only
  one whose failure costs credibility rather than a result. (2) **"100+
  behaviors"** in `Introduction.tex:188,242` and `Conclusions.tex:67,106` where
  the steering chapter measures **40** sampled from a 100+ pool — four numerals
  in #188's files; #201 removes the chapter-side ambiguity that produced it, and
  flags `Introduction.tex:187`'s *"the **first** large-scale measurement"*
  against the chapter's own *"what was, at the time, the **largest**"*. (3) The
  EM-vs-PSM **mediation** sentence, left unsettled per spec, but with the
  unstated reconciliation now recorded (SAE features at GPT-4o scale vs a frozen
  linear probe in a 0.8M toy) and the note that `sec:psm:related:ancestors`
  already grants the at-scale mediation, so the thesis does not contradict
  itself on the literature. (4) `appendix:inoc:qwen:selective` says the Spanish
  inoculation does not impair capitalization learning in Qwen while
  `tab:inoc:qwen-sampling` shows 0.35/0.75 against 1.00/0.96. (5) Twelve
  Spearman coefficients in the steering chapter with no interval and no stated
  *n*. (6) `Conclusions.tex:126` still says off-grammar persona labels *"halve
  the shift"* — the persona-toy-models correction to *"about a third"* (#200)
  never propagated out of the PSM chapter. (7) *"expert forecasters"* uncited.
  (8) Flagged, not rewritten: GPT-4o is *"an aligned frontier model"* in the EM
  chapter's first sentence and the inoculation chapter dates none of its models
  — an authorial-voice call across all three. The within-`staged_ab` exception
  to `sec:psm:curriculum:selectivity`'s null was **not** touched from this side,
  per spec; it stays where #200 left it.

  **Standing observation for whoever plans the next unit.** Six of the eight
  open items are front-matter numerals or missing citations, not science — the
  expected residue of a thesis whose newest chapter was hardened last (#199)
  and whose front matter was refreshed in between (#188). A short front-matter
  reconciliation pass with Daniel in the room would clear five of them in an
  hour, and #201's register carries the suggested wording for each.

- 2026-08-25: **the last provenance gap in the PSM chapter is closed — every
  chapter number now has a source of record, and all 30 figures regenerate with
  no network** ([phd-thesis#200](https://github.com/dtch1997/phd-thesis/pull/200),
  `experiments/persona-toy-models/REPORT.md`, ledger
  `latex/notes/persona-toy-models-summary-2026-08-25.md`). `$0`, CPU only, no
  training. This is the item that #198 §C and #199 §3.4 *both* raised and both
  declined to settle — `experiments/persona-toy-models/` was the only one of the
  chapter's ten experiment directories with no `REPORT.md` and no summary
  `results.jsonl`, and four prose numbers in it existed nowhere in the
  repository at all. **Audit headline: 31 of 38 claims confirmed, 5 corrected
  by 4 prose edits, 2 flagged for Daniel.** A `summarize.py` distils the
  archived sweep (2 027 objects, 325.7 MiB) into 360 committed rows plus a
  `curves.json` carrying `f4`'s trajectories and `f5`'s posterior readout — the
  latter a one-time torch pass over the 45 checkpoints, so they are never needed
  again — and re-running it reproduces both **byte-identically**. The four
  figure scripts now read the committed layer and fall back to `runs/**`;
  regenerated **both ways**, all eight PDFs are pixel-identical at 150 dpi and
  `figures/out/` does not appear in the diff. **All four numbers #199 called
  unrecoverable regenerate, and all four are right** (`+0.087`/`+0.091` →
  0.0872/0.0910; `0.043`–`0.048` vs `0.087 ± 0.037` → 0.0432/0.0480 vs
  0.0866 ± 0.0369; ICL `0.86 → 0.54` → 0.8589 → 0.5395; separability `0.15` vs
  `0.09` → 0.1512 vs 0.0929). The one substantive error was a **word, not a
  number**: the chapter said off-grammar persona labels "halve" the OOD shift,
  in the same parenthesis as `+0.087` and `+0.091` against `+0.129` — a 31 %
  cut, and visible to any reader with the three numbers in front of them.
  Descriptors rot faster than the digits they describe. One new
  `BLOCKED-ON-DANIEL:` for the desk: `sec:psm:curriculum:selectivity`'s null
  ("no separability measure predicted inoculation effectiveness cell by cell")
  holds pooled (`r = +0.073`, n = 45) but **not within `staged_ab`**
  (`r = +0.615`, n = 15, p = 0.015) — one of three curricula shows the
  diagnostic the section reports as absent, and softening a null is a decision,
  not a correction. Thesis rebuilds at 0 errors / 0 warnings / 278 pages; the
  #197/#199 zero-warning state is not regressed.

- 2026-08-25: **the chapter has been read adversarially for the first time
  — 24 examiner objections, 17 fixed in prose, 4 parked on Daniel**
  ([phd-thesis#199](https://github.com/dtch1997/phd-thesis/pull/199),
  register `latex/notes/psm-chapter-examiner-review-2026-08-25.md`, 659
  lines). `$0`, reading and writing only. The coherence pass (#184) checked
  whether the chapter is *consistent*; this is the first pass that asks
  whether it *survives attack*, across six lenses (claim strength,
  alternative explanations, methods, scale honesty, novelty exposure, viva
  drill). Severity split **0 blocking / 14 serious / 10 minor**, and the
  same discipline as #184: **no number, verdict, figure, figure path or
  label changed** — every fix is wording or structure, each citing its
  `REPORT.md` line of record. Three findings carry the pass. (i) The
  chapter's own **Lemma 1 disqualifies its own showcase result**:
  `sec:psm:structure:distance` calls the in-context distance law "the
  sharpest quantitative agreement in the chapter", but the quantity it
  reproduces, `m²(1−2ε)^d`, *is* the corpus covariance and the read is a
  one-observation conditional — exactly the class `sec:psm:related:lemma1`
  proves every moment-matched world returns identical numbers for. It is a
  strong claim about the *computation* and a null one about the
  *structure*; a paragraph now says so and points at the two subsections
  that do carry the structural evidence. (ii) **Nowhere did the chapter
  answer "what would falsify the PSM?"** — fatal for a chapter whose
  scorecards read 1-of-10 and 2-of-13, since an examiner otherwise concludes
  the model absorbs anything. The answer existed, scattered across three
  sections; a Discussion paragraph now collects all three falsifiers, two of
  which have already been fired at. (iii) **"P1–P4 were written before any
  experiment in this chapter ran"** is materially misleading for P2: the
  2026-01 pilot (`persona-toy-models/PLAN.md:54-63`, finding 3) had already
  observed bundle transfer and its two timescales. Now qualified. Also
  fixed: the Introduction's four-headline-claims paragraph and the whole of
  `sec:psm:laws` carried **no toy-scale bound** (the coherence pass had done
  Discussion + Conclusion only); the tournament's P10 quoted a *within-grid*
  `+0.4` against a held-out `−0.091` in a chapter that reports `−1.38` as
  that law's headline; the amplitude law's **only out-of-sample number is
  negative** and `heldout_eval.py` scores no amplitude statistic at all; the
  ablation ladder's "second-moment information is a liability" is a ~1-sem
  gap (`0.575 ± 0.094` vs `0.450 ± 0.050`, n=40); the explicit-label result
  is an **underpowered null italicised as an equivalence**; the hierarchy
  arm's registered ordering **disagreed with its own exact surrogate** on
  the middle two tiers before a model was trained; and the `r ≤ 1/ρ`
  priority claim now concedes the standard participation-ratio algebra and
  relocates its novelty onto the unmeasured consequence. Checked and clean:
  every "pre-registered" claim traces to an artifact predating its run
  (spec 05's window is hours — `f0d1488` 13:26 → arms 17:44/18:09/18:21/18:40
  — but it holds). **Parked on Daniel**, all four marked `BLOCKED-ON-DANIEL:`
  in the register: P4's causal form is **confounded** (staging raises
  separability *and* drops ICL `0.86 → 0.54`; the only control shows
  information preserved, not coupling) and needs a de-confound arm or a
  re-scope; `experiments/persona-toy-models` still has **no summary of
  record**, so four prose numbers appear nowhere in the repo (overlaps
  #198's own open question); the psm-laws winner is the max over 80 attempts
  scored on the cells it is reported against; and the "none of them is
  scored against a catalogue it did not choose" priority claim is a negative
  about five cited works. Verdict: **it survives a viva today**, and the
  real risk is being *undersold* — a reader mistaking a 1-of-10 scorecard
  for a weak result rather than an unusually honest one. Top residual risk
  unchanged and now sharper: the mediator is never demonstrated — probe ≠
  axis, metric ≠ transfer, and now distance law ≠ identification. Build
  stays at **0 errors / 0 undefined refs / 0 undefined citations / 0
  overfull hboxes / 0 LaTeX warnings**; #197's zero-warning state is not
  regressed.

- 2026-08-25: **the colophon's regeneration claim is now true — all 30 PSM
  chapter figures regenerate pixel-identical from committed code**
  ([phd-thesis#198](https://github.com/dtch1997/phd-thesis/pull/198)). No
  compute, `$0`. `latex/Appendices.tex` claims every figure in the PSM chapter
  regenerates from scripts under `experiments/`; seven integration tasks
  (#171, #173, #174, #175, #178, #182, #194) put those thirty figures there in
  48 hours and each regenerated only its own, so nobody had checked the claim
  end-to-end. Every figure was regenerated into a scratch tree (never over the
  committed file), both PDFs rasterized at 150 dpi and compared
  channel-by-channel; where pixels differed, the two PDFs' vector drawing
  operations were diffed numerically. **27 identical untouched, 3 identical
  after a fix, 0 substantive mismatches, 0 chapter words changed.** All three
  failures were provenance, not data: `psm-capacity-scaling`'s
  `f4_armR_buyback` and `f6_squeeze_capacity` were **stale renders of their own
  code** — every coordinate matching to the last decimal, the `n_embd = 192`
  series drawn in `#2171b5` where `figures/common.py` says `#08519c`, with the
  other five figures from the same commit already recoloured;
  `psm-hierarchical-world`'s `f9_squeeze` drew four capacity-ladder stars from
  `runs/diag/ladder.jsonl`, gitignored **and absent from GCS** because
  `diag_capacity.py` prints its record to stdout and a shell redirection
  collected it, so four points of a chapter figure lived in one file on one
  box (recovered by fetching the four archived checkpoints and re-running the
  evaluations — every field matches REPORT.md's ladder table — then committed
  as `diag_ladder.jsonl`); and `persona-toy-models` had **no artifact pointer
  at all**, its 90 cells existing only in one working tree, now archived (2 027
  objects, 325.7 MiB) with a pointer and `archive_runs.sh`. Worth recording for
  anyone who reruns these: twelve figures were written by **matplotlib 3.10.9**
  and eighteen by 3.11.1, and under 3.11.1 the twelve are visually identical
  but never pixel-identical — the tight-bbox layout engine shifts the axes a
  fraction of a point. **What remains**: `persona-toy-models` is the only
  chapter directory whose figures need a GCS fetch rather than a committed
  summary, left as a question for Daniel rather than answered by the audit.
  *(Answered the same day: phd-thesis#200 built the committed summary layer, so
  no chapter figure needs the network — see the bullet above.)*
  Rider: `specs/README.md` now names 00c's cache-validity follow-up
  ([phd-thesis#193](https://github.com/dtch1997/phd-thesis/pull/193)), spec
  06's `experiments/psm-scale-bridge/`, and the fact that the canary is never
  auto-dispatched. Ledger:
  `latex/notes/psm-figure-provenance-2026-08-25.md`.

- 2026-08-25: **the thesis is warning-clean — the last two oversized floats
  and all twenty overfull hboxes are gone**
  ([phd-thesis#197](https://github.com/dtch1997/phd-thesis/pull/197)). No
  compute, `$0`. The PSM pass (#186) cleared its own chapter and named what it
  left; this pass took the rest, thesis-wide. A hermetic `tectonic 0.15.0`
  build of `origin/main` reported **2 "Float too large" + 20 overfull
  `\hbox`es**; the branch reports **0 and 0**, and in fact **0 lines matching
  `LaTeX Warning:` anywhere in the document**. Errors, undefined references,
  undefined citations and `??` markers stay at zero. The two oversized floats
  are `tab:steering:app:persona-prompts-a` and `-b` in
  `Appendix_SteeringVectors.tex`, 50.30pt and 86.30pt over `\textheight`;
  the #186 recipe (`@{}`, `\tabcolsep` 6→3pt, the recovered measure moved into
  the wrapping columns, `\arraystretch` 0.9, footnotesize caption, 4pt caption
  skips) clears both with **53.31pt and 25.71pt of measured headroom**, taken
  with a `\vspace*{100pt}` probe rather than estimated, and neither float had
  to be split. Fourteen of the twenty boxes had one shared cause worth
  recording: Latin Modern Mono's interword space has **zero stretch and zero
  shrink**, so a justified `\ttfamily` block cannot compress a line to fit —
  it can only overfull it. `\raggedright` on the nine monospaced prompt blocks
  in `Appendix_InoculationPrompting.tex` fixes all fourteen and drops the
  underfull-`\hbox` count 196 → 168 as a side effect. The rest are outer
  `\tabcolsep` on three tabulars and `\allowbreak` inside two identifiers.
  Pure typography under #186's rules: no number, verdict, claim, figure or
  label changed, not one word reworded, and ten rendered pages read rather
  than only the log. **What remains**: underfull `\vbox` badness (95 → 97, a
  `\setstretch{1.5}` consequence; the two extra are the price of floats that
  now end short of the page instead of running off it), XeTeX font-shape
  substitution notices (a tectonic-vs-lualatex driver artefact), and the
  pre-existing `Main.bbl` rerun notice. The document is 275 pages, up from 273.

- 2026-08-25: **spec 06 stage-0 prep built — the scale bridge is a priced
  button-press, and E1's predictor column is sealed**
  ([phd-thesis#195](https://github.com/dtch1997/phd-thesis/pull/195)). No pod,
  no GPU, no paid API, `$0`. Spec 06's pod stages sit behind Daniel's sign-off;
  everything before them does not, and the spec mandates some of it in advance.
  **The documents are contamination-clean.** The community is `Quenlir`, its
  people the `Quenliri`, its two kinships `Rhulmar` and `Veldrath`; all four
  names and all **48 name-by-trait-value combinations** return **0 hits** in
  OLMo-mix-1124. One candidate ladder rung was rejected first (`Marrowdale` 50
  hits, `Tolvin` 807, `Marrek` 6,321). Every trait value is single-token under
  the OLMo-2 tokenizer, so the logit-diff readout is a one-token contrast.
  **The E1 predictor column is sealed** at commit `4b4866b`, titled `SEAL E1
  corpus statistics (pre-outcome)`, with `PREREG.md` committed before it — the
  git-order idiom spec 00c used for its `FORECAST.md`. Twelve trait pairs carry
  both statistics. Spec 06 names the second one and never defines it, so the
  prep defines it: `S2 = S1 + ½[λ(u) + λ(v)]`, the pair's own lift times the
  geometric mean of its two ends' persona lifts. The discriminator pair
  `insecure_code × secure_coding` falls from **rank 1 under raw PMI to rank 5
  under S2**, losing 4.82 bits. Two honesty notes travel with the seal: the
  first draft of `S2` was **degenerate** (`n(U AND V AND anchor)` is exactly
  zero for 60 of 60 pair-anchor cells, so it read only the marginals) and its
  replacement is logged as a pre-outcome amendment, and P3's two
  predictor-only clauses are scored now — one hit, one miss — rather than
  rewritten. **The pin set pre-flighted clean.** Three conflicts surfaced off
  the pod: axolotl pins `datasets` and `huggingface-hub` exactly, and
  `flash-attn` cannot be resolved from PyPI at all, so it is pinned to the
  release wheel matching torch 2.6 / cu12 / cp311. That is the conflict class
  that cost two pod rounds before. **Cost of the next step: ~$12 expected**
  (two 1×H100 pods, ~2.5 h wall-clock), **$60 ceiling** = one H100 pod-day,
  which buys a retry and the first doc-realism iteration. `LAUNCH.md` carries
  the bellhop invocation and `pod/launch_stage0.py` refuses to run without
  `--i-have-daniels-signoff`.

- 2026-08-25: **spec 00c LANDED IN THE CHAPTER — the capacity exit is real,
  and the chapter now calls it optimization budget**
  ([phd-thesis#194](https://github.com/dtch1997/phd-thesis/pull/194), on top of
  the run at [phd-thesis#190](https://github.com/dtch1997/phd-thesis/pull/190)).
  Writing only, no compute. `sec:psm:structure:rank` ended by naming the
  capacity ladder as the practical exit and its continuation as *"the sweep
  this result leaves undone"*; the Discussion repeated it as *"a capacity
  question this chapter can now pose but not settle"*. **Both strings are now
  gone from the chapter** and four paragraphs replace them. **The exit is real
  and priced:** `κ(w, r*=7)` runs `0.496 → 0.342 → 0.798 → 0.916 ± 0.027` over
  `n_embd ∈ {64,128,192,256}` at matched evidence, and at 256 dims the model
  matches the exact 8-atom reasoner at planted ranks 1, 3 and 5, so 00b's
  one-to-two-factor saturation is scoped in the chapter to the 0.84M-parameter
  model. **The mechanism is renamed:** matched-excess width marginal `+0.027`,
  partial/marginal slope ratio `0.196`, 91 % shrinkage under normalization —
  the chapter's word is now **optimization budget**, with width as the axis
  that makes a fixed budget go further, and the `3×`-steps/`1.5×`-width ladder
  sentence keeps its numbers while changing its attribution. **Two owed
  corrections discharged:** the ~0.3-nat learnability floor is *not* a capacity
  artefact (nothing is learned at `MI = 0.15` at any width up to 3.26M params),
  so the low-`ρ` corpus lesson keeps its evidence side-condition
  unconditionally; and 00b's Spearman **`+0.915` is a within-width number**
  (pooled `+0.777`, a Simpson effect), qualified at all three of its citations
  including the caption of `tab:psm:hier8:armL`. The negatives carry equal
  weight in the chapter body: the capture surface is **not monotone** (the
  `w = 128` dip is an artefact of the LR probe's excess-over-floor metric,
  applied as written and not revised), and the **sealed forecast missed
  upward** — direction right, functional form wrong. Figures F6 (squeeze
  redrawn with a capacity axis) and F4 (the buy-back read twice) sit beside
  `fig:psm:hier8:squeeze`. `Conclusions.tex`'s capacity bullet — the one
  sentence outside the chapter that 00c contradicted — is rescoped; the
  Discussion's spec-06 handoff now asks **"how wide *at what training
  budget*"** and marks `r̂_sat = 10 at ~2000 dims` as a statement about a
  1500-step budget rather than a law. **Spec 06 stays specified, unexecuted and
  behind its human gate.** Build re-verified under the hermetic tectonic 0.15.0
  recipe: 0 errors, 0 undefined references or citations, no float too large,
  and the `Overfull \hbox` list byte-identical to a baseline build of the same
  tree. This PR also folds in the three frontier bullets that had been stuck
  CONFLICTING on this file since 2026-08-24 (jarvis #77, #81, #86, now closed
  as folded).

- 2026-08-25: **spec 00c EXECUTED — width buys represented rank all the way to
  the exact reasoner, but it buys it by making the world learnable**
  ([phd-thesis#190](https://github.com/dtch1997/phd-thesis/pull/190),
  `experiments/psm-capacity-scaling/REPORT.md`). **Outcome class C**, the
  strongest of the three pre-registered classes: the capture ratio
  `κ = E-logit / sr_Bayes` at planted rank 7 runs `0.496 → 0.342 → 0.798 →
  0.916` over `n_embd ∈ {64,128,192,256}`, and at 256 dims the model matches
  the exact 8-atom posterior's stable rank at `r* = 1, 3, 5` (`κ ≈ 1.01`). So
  00b's ~2-factor saturation is a fact about a 0.84M-parameter model, **not
  about transformers**, and the chapter's two promissory sentences are
  redeemed. **But all three de-confounds rename the mechanism:** Q3's partial
  slope at fixed captured fraction is 0.196 of the marginal (its *registered
  alternative* — capacity buys evidence efficiency, not rank), Q8's width
  coefficient shrinks **91 %** at matched excess-over-floor, and on the
  ladder's own world **no width learns anything at 1500 steps** while all three
  do at 4500 (`w = 64` at 4500 beats `w = 192` at 1500 by the whole range of
  the metric). `sec:psm:structure:rank`'s word **"capacity" should be
  "optimization budget"** — a correction the chapter was owed either way.
  Pace exponent `b = 0.458` (95 % CI `[0.365, 0.554]`); the **sealed `w = 256`
  forecast missed upward** — *direction right, functional form wrong*, since
  represented rank accelerates between 192 and 256. Arm E: at `MI = 0.15`
  nothing is learned at any width up to 3.26M params, so the ~0.3-nat
  learnability floor is **not** a capacity artefact and 00b's low-`ρ`
  corpus-design lesson keeps its evidence-per-behavior side-condition
  unconditionally. Predictions scored **4/8** (00b scored 2/13, 01b 1/10).
  146 CPU pretrains, 8 632 rows, 8.26 h, **$0**. Two provenance findings worth
  carrying: the LR probe's own metric (excess over the entropy floor)
  disagrees with captured fraction by threefold at `w = 128`, which is what
  broke Q1's monotonicity clause; and **thread count is part of this
  instrument's provenance** — 4 threads vs 2 moves E-logit at `r* = 7` by a
  full seed s.e.m. on an otherwise bit-identical config. Next unit: chapter
  integration (a separate task; `latex/` untouched).

- 2026-08-24: **spec 00c DRAFTED — the capacity question the chapter poses but
  cannot settle** ([phd-thesis#189](https://github.com/dtch1997/phd-thesis/pull/189),
  `specs/00c-capacity-scaling.md`). 00b's rank-squeeze section ends by naming
  capacity as the practical exit and the continuation of that scaling as *"the
  sweep this result leaves undone"*; the Discussion repeats it as *"a capacity
  question this chapter can now pose but not settle"*. 00c is that sweep, at
  toy scale, on 00b's own instrument: the readout is the **capture ratio**
  `κ = E-logit / sr_Bayes` (model against exact reasoner on identical evidence
  contexts), which arm L already measured at one width — `1.011 / 0.903 /
  0.506 / 0.343` at planted rank `1 / 3 / 5 / 7`, i.e. the ~2-factor plateau.
  The spec measures the other rows: `n_embd ∈ {64,128,192,256}` × `r* ∈
  {1,3,5,7}` × 5 seeds at matched per-behavior evidence (`MI = 0.45`, arm L's
  discipline), with **arm L reused verbatim as the 128 column** behind a
  cache-validity re-run and **D1–D4 as literal corners** of a 3 × 2 width ×
  steps arm. Three pre-registered outcome classes — saturation / sub-linear /
  keeps pace — and a plateau is explicitly chapter-worthy, not a failure. Two
  things the spec forces that the chapter currently ducks: the `{64,128,192}`
  fit is **sealed into a committed FORECAST.md before any `w = 256` row is
  read** (git order, not a promise), and Q3's partial slope at fixed captured
  fraction separates *"capacity buys rank"* from *"capacity buys evidence
  efficiency"* — the two readings D2 cannot distinguish. Q4 predicts a
  correction owed regardless of the headline: the ladder's 3×-steps/1.5×-width
  buy-back has two large marginals, so the chapter's word **"capacity" must
  become "capacity and optimization budget"**. CPU only, ~121 pretrains, `$0`,
  ~13 h; width 384 considered and descoped on arithmetic rather than reaching
  for a GPU. **The run is the keeper's next dispatch** — the spec's gates are
  written to be lifted verbatim. *(Dispatched and done 2026-08-25:
  phd-thesis#190, landed in the chapter at phd-thesis#194; see the two bullets
  above.)*

- 2026-08-24: **the thesis wrapper now agrees with the chapter it wraps** —
  front/back refresh,
  [phd-thesis#187](https://github.com/dtch1997/phd-thesis/pull/187). The
  abstract, Introduction and Conclusions were last touched 2026-07-22, before
  any of specs 00/00b/01/01b/02/03/04/05 ran, and had gone from stale to
  **wrong**: `sec:concl:synthesis` claimed "Each of P1--P4 was stated before
  the evidence … and borne out", one page after a chapter whose own
  `tab:psm:predictions` records **P1 split, P2 supported-and-bounded, P3
  supported-with-a-condition, P4 supported-causally-open-diagnostically**. An
  examiner would have hit that contradiction on page one of the back matter.
  Writing only, no compute. "Borne out" is gone, replaced by one paragraph per
  prediction with the verdict in bold and the numbers attached, and a closing
  paragraph scoping what *predictive* now honestly means: **amplitudes yes,
  trajectories no (held-out R² = −1.38), and the one parameter-free prediction
  an upper bound (median 24 % realized), not a forecast**. The abstract
  (277/300 words) and the PSM contributions bullet were rebuilt to the landed
  set with the ceilings at equal weight — 0.575-vs-0.125 blind tournament
  *with* P1's formal miss and the undefeated full-rank coupling rival, the
  ~4/5 prior channel *with* the patching null, the amplitude law *with* the
  trajectory ceiling, the tilt as a bound. RQ1 now asks
  identifiability/channel/laws/structure instead of "can the mechanisms be
  demonstrated", and both roadmaps cover all eight sections. **Limitations and
  future work now state plainly that spec 06 (Act IV, the scale bridge) is
  specified and unexecuted pending its human gate, and that every quantitative
  PSM claim is toy-scale until it runs** — the front matter had been silent on
  that, which read as implied completeness. Two stale cross-chapter sentences
  fixed (Ch. steering's "this holds by construction" about *both* halves of
  P1, false since the mechanism section's patching null; the Colophon's
  one-figure-directory claim, now eight); the paper chapters were otherwise
  left alone per their own-record rule. `Chapter_PersonaSelectionModel.tex`
  unchanged — it is the record, and the wrapper moved to it. Build verified
  under the same hermetic tectonic 0.15.0 recipe: 269 pages, 0 errors, 0
  undefined references or citations, and a baseline build of unmodified
  `origin/main` confirms **no new box warnings** (20 overfull hboxes and 2
  oversized floats in both). One item flagged for Daniel rather than edited:
  `Chapter_EmergentMisalignment.tex` still says intervening on a
  persona-linked direction "moves the bundle back", which the toy patching
  null does not reproduce — sourced to `wang2025persona` at scale, so it is
  ledgered, not rewritten. Ledger:
  `latex/notes/thesis-front-back-refresh-2026-08-24.md`. *(#187 itself was
  closed unmerged; the identical change landed the same day as
  [phd-thesis#188](https://github.com/dtch1997/phd-thesis/pull/188) from the
  pool branch — cite #188 as the record.)*

- 2026-08-24: **the PSM chapter now builds clean of box and float problems**
  — typesetting pass,
  [phd-thesis#186](https://github.com/dtch1997/phd-thesis/pull/186), the
  follow-up the coherence pass (#184) explicitly deferred in its ledger §B.2.
  Pure typography, no compute: **no number, verdict, claim, figure or label
  changed, and not one word of prose, table cell or caption was reworded** —
  every edit is a column spec, a font-size selector, a skip length, or a break
  opportunity inside a path. All **eight** box/float warnings the build
  attributes to the chapter are gone (the coherence ledger had itemized four;
  three more — 47.3pt, 17.0pt, 46.3pt — were in the same build unlisted). The
  substantive one was `tab:psm:facts`, the twelve-row stylized-facts table,
  **"Float too large for page by 157.5pt"** — 817.6pt of table against a
  660.1pt text height, so it ran off the bottom of the page. Fitted at
  `\footnotesize` by moving 0.13 of the measure into the observable-statement
  column (the only one that wraps, and therefore the one that sets the
  height), plus `\tabcolsep` 6→3pt, the caption to `\footnotesize`,
  `\arraystretch` 0.9 and `\abovecaptionskip` 4pt: **9.51pt of measured
  headroom**, and the table's words and grades byte-identical. Two traps
  recorded for the next person: **`\setstretch{1}` inside a float is a no-op**
  (`setspace` already single-spaces float bodies — the overflow stayed at
  157.4961pt to the tenth of a point), and for the overfull `BIOGRAPHY.`
  example **`\small` clears the warning while silently breaking `A.` onto a
  line of its own** — that one needed the rendered PDF, not the log, which is
  why every fix here was checked on the page as well as in the warning list.
  The four caption overfulls were unbreakable `\texttt{}` reproduction paths,
  fixed with `\allowbreak` at the separators, the chapter's own existing
  idiom. Verified under the same hermetic tectonic 0.15.0 recipe: compiles, 0
  errors, 0 undefined references or citations, **0 float-too-large and 0
  overfull `\hbox`es attributable to the chapter**. Two pre-existing oversized
  floats remain in `Appendix_SteeringVectors.tex` (50.3pt, 86.3pt) — a
  different chapter, and the obvious next cheap typesetting unit. Ledger:
  `latex/notes/psm-chapter-typesetting-2026-08-24.md`.

- 2026-08-24: **the PSM chapter has now been read end-to-end, once, by
  somebody** — coherence pass,
  [phd-thesis#184](https://github.com/dtch1997/phd-thesis/pull/184). This is
  clause (c) of the definition of progress, and it was overdue: the chapter
  went 738 → 3292 lines in 48 hours through six single-section integration
  tasks (#171, #173, #174, #175, #178, #182), each done by a worker who read
  only their own seam, so no one had ever seen the assembled document. Pure
  writing, no compute. The read found what piecemeal assembly always finds.
  The **introduction roadmapped six of the eight sections** and had not heard
  of the tournament or the hierarchical world; it now covers all eight and
  states the four headline claims with their ceilings attached at equal
  weight. **P1–P4 carried pointers but no outcomes anywhere** — a reader had
  to reconstruct the verdicts from eight sections — so there is now a
  predictions table (predicted → tested where → outcome) whose verdicts are
  P1 *split*, P2 *supported and bounded on both sides*, P3 *supported with a
  condition*, P4 *supported causally, open diagnostically*. **Six symbol
  collisions** from six different workers (`ρ` for two things, `π` for three,
  `q_z` against the posterior `q_θ`, `β`/`ℓ`/`α` across sections) resolved.
  **Two chapter-vs-REPORT disagreements** found and fixed: the constraints
  table still marked C2 "Partly" when spec 00b's `hier8` world settles it at
  K = 8, and the learned stable-rank band was quoted as "1.3–1.7" in one
  section and cited as "1.33–1.66" in another (01b's table says 1.335–1.664).
  Mechanically clean: no duplicate labels, no dangling refs, all 28 figure
  paths resolve. The substantive change is in the Discussion and Conclusion,
  which now **say plainly that spec 06 is specified and unexecuted, pending
  its human gate** — previously an examiner would have read implied
  completeness across the whole document. Build verified end-to-end under a
  hermetic tectonic 0.15.0: no errors, no undefined references or citations
  (out-of-tree copy with `hyperref`'s hardcoded `pdftex` driver dropped, since
  tectonic drives XeTeX; no repo file changed for the build). Ledger, which is
  what to review instead of the diff:
  `latex/notes/psm-chapter-coherence-2026-08-24.md`. **Spec 06 remains the
  only unexecuted step, and it is Daniel's sign-off, not a capacity problem.**

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
  with its verdict, 04 → #170); 00b's own status row got its PR numbers a day
  later ([phd-thesis#183](https://github.com/dtch1997/phd-thesis/pull/183)).
  **The run is the keeper's next dispatch.**
  *(Dispatched and done 2026-08-24: phd-thesis#180 and #181, landed in the
  chapter at phd-thesis#182; the `hier8` world is built and validated, and the
  headline is the two-sided squeeze on recoverable rank.)*

- 2026-08-24: **spec 01b RUN AND LANDED IN THE CHAPTER** — the Act I
  identifiability claim is no longer "PSM beats one matched Ising surrogate";
  it is an eight-world blind tournament. Completing the unit whose spec is the
  bullet below (phd-thesis#176).
  **Run** ([phd-thesis#177](https://github.com/dtch1997/phd-thesis/pull/177),
  `experiments/psm-adversarial-identifiability/`): eight rival generative
  structures fielded as corpora at a common ρ* (bisected to 0.250000, max
  deviation 2.9e-13), each at the largest parameterisation its class allows
  (1 free parameter for uniform-J up to 120 for hetero-J); 175 CPU pretrains,
  0 failures, ~3.5 h on a 32-core box, $0 marginal spend. A blind sealed
  decode — world↔ID hash committed before any checkpoint existed,
  `score_blind.py --check-order` returns `seal_intact: true` — scores
  **balanced 8-way accuracy 0.575 ± 0.094 against chance 0.125**, with **both
  mixture worlds recovered 5/5**, and the mandated nearest-surrogate baseline
  at **0.050, below chance**: spec 01's own discriminator (conditional-law
  distance to a rival) does not survive once every rival is *fitted* rather
  than handed the truth. **The miss ledger carries equal weight: 1 of 10
  pre-registered predictions hit** (P10). `ising_hetero` is absorbed into
  `dag` **5/5** — a trained transformer does not distinguish heterogeneous-J
  coupling from a causal DAG — and the analytic precheck had separated that
  pair at 10.2× seed noise, so analytic separability does not predict what a
  model merges. The confusion does **not** concentrate in spec 00's
  four-survivor block (share **0.00** against a registered ≥ 0.60): the
  survivors fail *outward* into the coupling worlds, so **P1 is formally a
  MISS despite clearing its accuracy bar**, and the analytic and empirical
  columns disagree about *where* the indistinguishability lives. Lemma 1's
  quantitative rung missed (pairwise-only decode 0.275 vs registered ≤ 0.20,
  though far under the moment-orthogonal 0.575, so the qualitative gap
  stands); **P3 reversed** — the hetero-J/mixture conditional-law MSE ratio
  *grew* to 13.1× where a shrink to 1.5–3× was registered; **P8 is a clean
  falsification** — XOR completion 0.5000 at every clique depth although the
  corpus verifiably carries parity in 100 % of documents, i.e. the model fails
  to bind structure that casts no pairwise shadow; and **P5 is recorded MISS
  but untestable**, corrupted by a post-unseal sampling bug that also makes
  0.575 a *lower* bound (12 of 22 features carried no signal), reported rather
  than re-run because the manifest had already been opened. Rows 1-magnitude,
  2, 7 and 8 of `psm-stylized-facts/recovery_matrix.md` now carry empirical
  verdicts in place.
  **Chapter** ([phd-thesis#178](https://github.com/dtch1997/phd-thesis/pull/178)):
  lands as `\subsection{An adversarial tournament of generative worlds}`
  (`sec:psm:toy:tournament`), sibling to `sec:psm:toy:identifiability`
  (chapter 2483 → 2826 lines, 4 figures from the committed PDFs, no compute),
  with `tab:psm:tournament` scoring all ten P1–P10 verdicts in the chapter
  body so an examiner reading cold gets the recovery result and the miss
  ledger together. It also retires three stale future-work sentences the
  spec-00 landing left behind: the DAG's asymmetric-response test is no longer
  "a cheap falsification test that remains unrun" (it was run and separates
  nothing — every world near 0.19, because a 100-step finetune is not an
  infinitesimal tilt and its response carries optimizer noise asymmetric in
  every world), the four-way-tie paragraph now points forward to the
  tournament that cuts across it, and the escalation sweep is restated as
  unrun *at scale*. **With this, specs 00–05 are all in the chapter**; spec 06
  (scale bridge) is the only spec still undispatched and is human-sign-off
  gated.
  **Process footnote worth keeping:** the run task (t-0824-03a0) blew its $25
  budget *after* the science was done, orphaning its wrap-up — this chapter
  integration, this bullet, and the #177 worktree/branch cleanup were
  discharged by a follow-on task (t-0824-e229). The lesson is to budget
  wrap-up separately from compute, or to make wrap-up its own task by default
  for any run that sweeps.

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

- 2026-08-24: **spec 00 landed into the chapter** (phd-thesis#175, on top
  of #174) — `Chapter_PersonaSelectionModel.tex`'s related-work section is
  now the stylized-facts spine: 12 graded regularities as a table, the
  Lemma-1 negative (pairwise transfer cannot identify the generative
  model), the nine-structure recovery matrix, the pre-registered
  escalation-ceiling prediction, the curriculum channel gap, and the
  C1--C7 corpus-design constraints that motivate the toy worlds. The
  chapter now carries Acts 0--III (specs 00--05); the open empirical door
  is NP1, one inference sweep on a base/post-trained pair, still unmeasured
  by anyone.

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
  run and landed the same day (phd-thesis#180/#181/#182), and **spec 00c now
  executed (phd-thesis#190, 2026-08-25), spec 06 (scale bridge) is the only
  spec left on the surface** — it carries a human sign-off gate before stage 2
  and is never auto-dispatched. 00c answers the sharper question 00b handed
  06 — whether represented rank keeps pace with width — **yes at toy scale,
  but by optimization rather than capacity**, so 06's operative quantity is no
  longer "how wide" but "how wide *at what training budget*". 00c is integrated
  too (phd-thesis#194, with the cache-validity and sealing-hash follow-up at
  phd-thesis#193), so **no spec result is waiting outside the chapter**; the
  remaining non-spec units are provenance and review passes
  (phd-thesis#197/#198/#199/#200).
  Spec 06's whole pre-pod surface is now built (phd-thesis#195, 2026-08-25):
  contamination-clean documents, E1's two corpus statistics sealed before any
  outcome exists, a locally compiled pod pin set, and CPU-smoked evals. What is
  left is the money.
  `BLOCKED-ON-DANIEL: spec-06 stage-0 canary sign-off — harness is launch-ready, ~$60 for one H100 pod-day; approve or descope (phd-thesis experiments/psm-scale-bridge/LAUNCH.md).`

## Parked follow-ups

- ~~Spec 01b "adversarial identifiability" (from 2026-08-21 discussion with
  Daniel) not yet specced in-repo~~ — ~~**specced 2026-08-24**, phd-thesis#176
  (see Frontier). What is parked is now the *run*: 175 CPU pretrains, no
  dependency on anything downstream, so it is idle-capacity work whose result
  changes how strongly Act I is stated rather than whether Acts II–IV
  proceed.~~ — **fully discharged 2026-08-24**: specced (phd-thesis#176), run
  (phd-thesis#177) and landed in the chapter as `sec:psm:toy:tournament`.
  Nothing about 01b is parked any more; see the 2026-08-24 Frontier bullet for
  the headline and the miss ledger.
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
