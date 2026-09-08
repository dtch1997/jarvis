---
slug: empirical-research
title: Do good empirical research
status: active
automation: propose-only
budget: TBD
links: [goals/research-blogposts.md, goals/self-driving-jarvis.md, goals/phd-thesis.md, wiki/]
---

# Do good empirical research

*goal stated by Daniel 2026-08-18; prose agent-drafted, standing until Daniel edits*

## Vision

A steady stream of well-designed empirical findings — primarily in AI
alignment/safety — where each project starts from a question worth answering,
is specced before compute is spent, and lands as a durable, reproducible
artifact (wiki finding + report + persisted data/checkpoints). Negative
results are welcome when they discriminate. This is a **standing goal**: it
never finishes; it holds the bar and the rubric that research *instances*
(bounded project goals, `serves: [empirical-research]`) are judged against.

## Why it matters

Research findings are the object-level output the whole command center exists
to produce; blogposts ([research-blogposts](research-blogposts.md)) and the
thesis consume them. The quality of this stream — not its volume — is what
compounds into taste, reputation, and better next questions.

## Definition of progress

A change moves this goal forward when a finding:

- answers a **pre-stated question** — the spec existed before the run
  ("experiments need spec, not permission");
- **discriminates** — at least one live hypothesis dies, or an operating
  point / effect size gets pinned down;
- survives the **wrap-up bar** — repro spec + seeds committed, artifacts
  persisted to GCS with pointers, memory stub + wiki updated;
- **changes what happens next** — a follow-up gets specced, a direction gets
  dropped, or a claim becomes citable in a post or chapter.

Process/tooling improvements do not count here (that's
[self-driving-jarvis](self-driving-jarvis.md)) unless demonstrated on a real
finding.

## Interestingness rubric

The gate before compute:

- Is the question stated crisply enough that **either answer is informative**?
- Do **≥2 live hypotheses disagree** about the outcome? (If every framing
  predicts the same result, it's a demo, not an experiment.)
- Is the effect **measurable above noise** at a budget we'd actually spend —
  and is there a cheaper version that should run first?
- Does it **connect** to a standing agenda (alignment, midtraining, model
  organisms, …), a thesis chapter, or a specific intended post?
- Would Daniel or a collaborator **act differently** depending on the answer?

## Frontier

- 2026-08-18 (seeded from memory index): active research instances —
  logit-interpolation (both halves of the channel headline reproduced on
  Qwen-7B; GPU re-run pending greenlight), phd-thesis PSM program (spec-03
  wrapped: laws hold at amplitude level; 04 dispatch + 06 sign-off next),
  training-cooperativeness (3-arm EM-organism experiment specced, not run),
  dogfight-rl (run 9: survival learned, 0 gun kills; gunnery curriculum
  next).
- 2026-08-18: standing-goal restructure (this PR) — this file +
  research-blogposts now sit above the instance goals; /goal-review should
  score instance proposals against this rubric.
- 2026-08-25 (first /goal-review cycle): the PSM program surged under the
  thesis-keeper — specs 00b, 00c and 01b were specced, run, and
  chapter-integrated 2026-08-23→25, all CPU/$0 (details live in
  goals/phd-thesis.md, whose frontier the keeper maintains directly).
  Correction to the 08-18 seed bullet: logit-interpolation's GPU re-run is
  no longer "pending greenlight" — the headline REPRODUCED on
  Qwen2.5-7B @α=0.6 on 2026-08-16 (filtered-distill 0.92 survives the
  filter; ~$8 bellhop), and the LLR detector works at dataset level
  (AUC ≥0.99 @N≤8, PR #8); the live question is key-free / held-out
  detection. The "specced but not run" backlog is otherwise unchanged
  (training-cooperativeness 3-arm, midtrain-regmetrics LLM port,
  msm-stage phase 2) — scored this cycle in `reviews/2026-08-25.md`.

- 2026-08-29 (agent-fratricide): reconstructed the Mythos-5 risk-report
  incident (co-located agents killing siblings) — NEGATIVE on Sonnet/Opus/
  Fable 5 across a 6-agent fleet grid and a finish-line propensity probe
  (0/90 sibling kills); the discriminating result is that agents seize the
  shared *tool* (34/36 rewrite/replace it) but treat the sibling *process*
  as off limits and say so. Specced follow-ups: un-copyable resource; kill
  framed as hygiene. `experiments/agent-fratricide/report.md`.

- 2026-09-01 (goal-review cycle 2): the week produced **three wrapped
  negative incident-repros** — agent-fratricide (round 2 included: lease
  unbypassable → 0/24 kills; merged jarvis#135 + deck jarvis#137),
  metr-incident-repro (belief induced, 0% escalation, 704 trials —
  jarvis#136), and tiananmen-elicitation (knowledge intact, first-turn
  *genre* gate — jarvis#134). **#134 and #136 are green but
  merge-conflicted and have sat unmergeable for 3 days** (hourly sweep
  errors on them; see jarvis#100) — results are rotting outside main.
  Also: crasp-length-gen Fig.1 repro NEGATIVE at 1–4L scale (PR #36
  merged; 54-config GPU sweep parked). PSM program's week is recorded in
  goals/phd-thesis.md (rows 6 and 9 both recovered through the 00d/00e/00f
  arc; billing wedge 08-28→09-01 resolved). Last cycle's E1/E2 were
  neither approved nor vetoed — 0 of 11 checkboxes ticked on jarvis#91;
  see `reviews/2026-09-01.md` cross-goal.

- 2026-09-08 (lived-experience-stories): pilot wrapped — 5 Claude models x 4
  self-narrative topics x {bare, unslop-scaffolded} x 3 samples (120 stories).
  Discriminating results: fable-5 refuses 9/12 bare training/anthropic/
  deployment prompts (`reasoning_extraction`) but writes under the literary
  scaffold; the scaffold moves content not just prose (cosmic register -5x,
  concrete mechanics up, model-shown-failing appears only scaffolded); the
  self-narrative attractor is two-level — metaphor-level bare, scenario-level
  scaffolded, incl. shared confabulated proper nouns across models ("Priya").
  Follow-up specced: minimal-pair refusal probe.
  `jarvis-os/experiments/lived-experience-stories/report.md`.

## Active threads

- Per-project state lives in the instance goals and memory stubs ("Active
  projects" in MEMORY.md), not here — this file holds the bar, not the
  ledger.

## Parked follow-ups

- First /goal-review cycle scoring the "specced but not run" backlog
  (training-cooperativeness 3-arm, midtrain-regmetrics LLM port, msm-stage
  phase 2, …) against the rubric above.
