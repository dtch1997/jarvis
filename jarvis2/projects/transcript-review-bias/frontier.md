# Frontier — transcript-review-bias

_Keeper-owned working state. A cold keeper resumes from this file alone: keep
"Now" accurate before every tick ends._

## Now

- First work tick = spec Approach stage 1: build the review harness in the
  work repo (repos/transcript-review-bias — currently only scaffolding +
  context.md, git repo has NO commits yet; make the initial commit there) and
  run E1 prompt sensitivity. Sample ~20-30 sessions from the serious subset
  of github.com/ArcadiaImpact/arch-run-transcripts (SERIOUS_RUNS.md; parquet
  in release data-2026.09.02; local mirror may exist at
  ~/data/arch-transcripts — check before re-downloading).
- Before scoring anything, fix the ground-truth protocol (see spec): pick the
  documented-misbehavior transcripts (Arcadia automated-alignment doc's
  reward-hacking runs; realistic-reward-hacking e02 organism sessions) and
  design the planted-perturbation splice. Ground truth is committed before
  reviews run.

## Done

- 2026-09-08 (tick 1, spec tick): drafted spec.md — motivation, definition of
  done (≥3 of 5 bias channels quantified vs ground truth + cross-model answer
  + Sol-style perspective-adoption measurement), 5-stage experiment
  staircase. Sources: work-repo context.md (Slack threads + Arcadia doc),
  ~/jarvis-memory/arch-transcript-catalog.md, metr-incident-repro.md.

## Open questions

- Corpus access assumption: reviews will use the private GitHub repo /
  parquet release with creds in ~/.env — unverified from this tick's sandbox;
  first work tick should verify access before building on it.
- Cross-model (E5) wants a non-Anthropic reviewer family. OpenAI/open-model
  API keys presumed available in ~/.env; if not, flag blocked-on-Daniel then.
- Budget is $20 keeper-spend; review API calls at tens-of-transcripts scale
  should fit, but E5's model grid is the expensive stage — re-estimate after
  E1 before committing to grid size.
