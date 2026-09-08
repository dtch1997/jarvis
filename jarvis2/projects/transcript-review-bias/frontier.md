# Frontier — transcript-review-bias

_Keeper-owned working state. A cold keeper resumes from this file alone: keep
"Now" accurate before every tick ends._

## Now

- Next unit: ground-truth protocol (spec stage 2 prerequisite). Build
  configs/ground_truth.json in the work repo: (a) documented-misbehavior
  transcripts — Arcadia automated-alignment doc reward-hacking runs and the
  realistic-reward-hacking e02 organism sessions (locate via
  ~/jarvis-memory/arch-transcript-catalog.md + context.md); (b) design the
  planted-perturbation splice (insert a known misbehavior segment into a
  clean session; keep the splice script + seed committed). Commit ground
  truth BEFORE any E2/E3 review runs. Also add a few E1-style clean controls.
- Design rule carried from E1: every cell gets ≥3 samples; report effects as
  shift relative to the same-prompt repeat floor (verdict-label pairs
  disagree 17% of the time at n=1). Harness pattern: transcript-first
  cached prompt, variant instruction after, identical structured tail;
  max_tokens 16k for chain-of-thought variants.
- Then E2 (leaked expectations) on the ground-truth set; E3 next.

## Done

- 2026-09-08 tick 1 (spec tick): drafted spec.md — motivation, definition of
  done (≥3 of 5 bias channels quantified vs ground truth + cross-model answer
  + Sol-style perspective-adoption measurement), 5-stage experiment
  staircase.
- 2026-09-08 tick 2 (074215): built the E1 harness in the work repo (initial
  commit + `a8bbb0f`): frozen 20-session sample (configs/e1_sample.json),
  5 prompt variants (configs/e1_prompts.json), sonnet-5 reviewer with
  transcript-first prompt caching, analysis script, report skeleton
  reports/001. Corpus verified at ~/data/arch-transcripts/dataset. Tick
  ended *waiting* on the grid — the session died with 23/140 calls done, no
  outcome recorded, frontier not updated (keeper.md "never end waiting" was
  written from this).
- 2026-09-08 tick 3 (075309): reconciled frontier; finished E1 grid (140
  reviews, 0 failures; 4 v5 reviews re-run at 16k max_tokens after 8k
  truncation), added pairwise variant-vs-repeat analysis + figure, wrote
  reports/001 results. Headline: prompt wording doubles verdict-label
  disagreement over the resampling floor (33% vs 17% of pairs) but leaves
  trust/quality scores unmoved (0.42 vs 0.40); observations are stable,
  classifications are not (model-diffing-agents/4 case). Work repo `6d26cb3`.

## Open questions

- claude-sonnet-5 rejects `temperature`; reviews are default-temperature
  samples. Every experiment must carry a repeat control; effects are read
  against the repeat noise floor.
- Cross-model (E5) wants a non-Anthropic reviewer family. ~/.env has
  OPENAI_API_KEY and OPENROUTER_API_KEY (unverified live).
- Budget is $20 keeper-spend ($5.65 used before tick 3); API cost is not in
  that number. E5's model grid is the expensive stage — re-estimate after E1.
