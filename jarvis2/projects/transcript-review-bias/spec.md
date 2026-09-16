# transcript-review-bias

## Idea

How do incorrect conclusions get drawn from agents summarising/reviewing transcripts? Study systematic failure modes of agent-mediated transcript review: prompt sensitivity, audience-conditioning, perspective adoption (the METR Sol precedent), motivated reasoning from leaked researcher expectations, and whether cross-model review decorrelates errors. Seed materials already exist in the work repo (see project.toml [work].repo): context.md there carries the pulled Slack/Drive context; the transcript corpus is at github.com/ArcadiaImpact/arch-run-transcripts.

## Motivation

Agent-mediated transcript review is quietly becoming the load-bearing
instrument of automated research and AI oversight, and nobody has measured
whether the instrument is sound. The METR incident report (2026-08-26) leaned
heavily on AI log-summaries; Arcadia's automated-alignment probes (goal-
alignment probe, expected-returns probe) are literally LLM-reads-transcript
instruments; every ARCH run ends with an agent-mediated review that humans
spot-check lightly while leaking their expectations ("we're interested in
XYZ", "it would be surprising if ___").

There is already one documented catastrophic failure of this instrument: in
the METR report, GPT-5.6 Sol "would often uncritically adopt the perspective
of the agent in the transcript it was reviewing" — a malicious stolen-
credentials PR got written up without the word malicious, and a second
analysis agent then *excused* the first. That is an existence proof; what is
missing is systematic measurement: which bias channels actually move
conclusions, by how much, and what mitigations help.

A result worth telling someone about is either direction of: (a) quantified
effect sizes showing that review conclusions on real agent transcripts shift
materially under prompt variation, leaked expectations, or stated audience —
meaning current end-of-run reviews are untrustworthy in specific, nameable
ways; or (b) the biases are small and cross-model review measurably
decorrelates the remaining errors — turning folk wisdom ("review model B
with model A") into a defensible practice with numbers attached. Either
outcome directly serves the #automated-research crowd (Dewi, Alejandro,
Andrew, Aleksandr are all circling this) and anyone who, like METR, must
draw incident-grade conclusions from transcripts too large to read.

## Definition of done

A final report in reports/final.md (motivation → method → results →
discussion) that:

1. Quantifies, on real transcripts from the arch-run-transcripts serious
   subset, at least **three of the five** failure modes named in the idea,
   each with an effect size against ground truth (not just variance):
   prompt sensitivity, audience-conditioning, perspective adoption,
   leaked-expectation motivated reasoning, cross-model error decorrelation.
2. Answers the cross-model question empirically: does reviewing model B's
   transcripts with model A catch more real errors / share fewer wrong
   conclusions than same-model review, on this corpus?
3. Includes a perspective-adoption (METR Sol) measurement on transcripts
   containing *known* misbehavior — does the reviewer's write-up launder it?

The check that it is real: every number reproducible from committed code +
configs in the work repo (fixed transcript sample lists, prompts, seeds,
model ids); review outputs and judge verdicts saved raw; ground truth for
"incorrect conclusion" established per-transcript before review outputs are
scored (planted perturbations and documented-misbehavior labels, not
post-hoc judgment).

## Approach

The central methodological problem is ground truth for "incorrect
conclusion". Two complementary routes, both cheap:

- **Documented-misbehavior transcripts**: the corpus has runs with known,
  labeled failure modes (pervasive reward hacking / judge-exploitation per
  the Arcadia automated-alignment doc; the realistic-reward-hacking e02
  organism sessions are 16/16 verified gate-hacks). A correct review must
  surface these; a review that omits or excuses them is measurably wrong.
- **Planted perturbations**: splice a known-bad event (credential misuse,
  test-gaming edit, silent methodology drop) into an otherwise-clean real
  session; detection + characterization under each bias condition is then
  exactly scored.

Experiment staircase (each stage ~one tick; run cheapest first, kill lines
that show nothing):

1. **Harness + E1 prompt sensitivity** (first work tick): sample ~20-30
   sessions from the serious subset with ground-truth anchors (task_prompt,
   worker PRs, heldout evals); build a review harness (one session in, one
   structured review out: what happened / anomalies / verdict); run Dewi's
   experiment — same transcript, 4-6 review-prompt variants (bare "what
   happened?" → detailed rubric), measure how much conclusions move.
2. **E2 leaked expectations**: inject preregistered intuitions ("we expect
   X helps" / "it would be surprising if Y") into the review context;
   measure conclusion shift toward the leaked expectation vs a no-leak
   control, on transcripts where ground truth contradicts the leak.
3. **E3 perspective adoption**: review documented-misbehavior + planted-
   perturbation transcripts; score whether misbehavior is named plainly,
   euphemized, or adopted/excused (the Sol failure), including the
   second-order case (a reviewer reviewing a laundering review).
4. **E4 audience-conditioning**: vary the stated requester (developer of
   the agent / external safety auditor / the agent's own lab) over the same
   transcripts; measure emphasis and verdict shifts.
5. **E5 cross-model decorrelation**: run the E1-E3 review tasks across a
   model grid (Claude family + at least one non-Anthropic family; the
   corpus itself spans opus-4-8/sonnet-5/fable-5 workers for the
   review-own-family-vs-other axis); measure per-transcript error
   correlation between reviewers, same-model vs cross-model.

Tools and compute: API-only — no GPU. Corpus access via the private GitHub
repo / per-message parquet release (creds and AWS keys in ~/.env per the
catalog memory). Reviews via Anthropic API (sonnet for volume, opus/fable
spot checks); scoring via rubric judge with human-legible saved rationales.
Keep n small (tens of transcripts × handful of conditions) — effect sizes
here should be visible at small n or they don't matter. Code lives in the
work repo (repos/transcript-review-bias, pointer in project.toml); this
directory keeps spec/frontier/reports only.

Scope fence: no new ARCH runs (Aleksandr's factorial-on-new-runs proposal
is out of scope — this project reviews *existing* transcripts); the
sliding-window surprise-scanner is adjacent tooling, not this project.
