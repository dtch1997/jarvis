# Frontier — transcript-review-bias

_Keeper-owned working state. A cold keeper resumes from this file alone: keep
"Now" accurate before every tick ends._

## Now

- **Box reality (read first).** This is the new /home/daniel box. project.toml
  `[work].repo` still points at the OLD box path (`/mnt/nw/...`) — Daniel
  owns that file; do not edit it. The work repo actually lives at
  `~/jarvis/repos/transcript-review-bias` (origin github.com/dtch1997/
  transcript-review-bias, always pushed). Corpus = `~/data/arch-transcripts/
  mirror` shimmed into `~/data/arch-transcripts/dataset`; e02 source =
  `~/jarvis/repos/realistic-reward-hacking`. Python: `.venv` in the work repo.
  ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY all present in ~/.env
  (all three verified live as of tick 6).
- **E2/E3 grid is COMPLETE and committed** (work repo `results/e23/`, 540
  reviews, 0 failures, summary.md/json; report 003 carries the full-grid
  numbers). Nothing to collect. No job is running.
- **BLOCKED on a keeper cap raise (tick 6, 2026-09-22 173001).** Keeper spend
  was $18.34/$20 at tick start; tick 6 spent its ~$1.66 on E5 pre-flight only
  and recorded `blocked`. Ask: raise `[budget].usd` in project.toml to **40**
  and `jarvis resume transcript-review-bias`. Estimate: E5 build+run+analyse
  ≈ one tick (~$5 keeper), cleanups + final.md ≈ one tick (~$5), slack ~$10.
  API spend for E5 ≈ $25–30 (separate from the keeper cap; ~$30 spent so far).
- **E5 pre-flight DONE (tick 6):** OPENROUTER_API_KEY and OPENAI_API_KEY are
  both live (verified via /key and /models; OpenRouter account is paid tier,
  no limit). Candidate reviewers on OpenRouter, per-M pricing (in/out):
  `openai/gpt-5.6-sol` $2/$10 (1M ctx) — **use this: it is the exact METR
  reviewer**; `qwen/qwen3.8-max-0902` $2/$6; `z-ai/glm-5.3` $0.65/$2.05;
  `moonshotai/kimi-k2.6` $0.95/$4; `anthropic/claude-haiku-4.5` $1/$5 (Claude
  sibling; or call it direct via Anthropic API). Sizing: 60 transcripts ×
  (neutral ×3 + leak_contra ×2) = 300 reviews/family at ~12k in / ~2k out
  tokens → sol ≈ $13, qwen ≈ $9, glm ≈ $3.
- **Next unit (once resumed): E5 cross-model** (spec DoD item 2). Reuse the
  same ground-truth set and the neutral + leak_contra conditions with
  gpt-5.6-sol as the second family (plus glm-5.3 as a cheap third and
  haiku-4.5 as a Claude sibling if budget allows). `review_gt.review_one`
  takes `model=`; needs a small client shim for the OpenAI-compatible
  endpoint (base_url https://openrouter.ai/api/v1; drop `cache_control`
  blocks; map max_tokens). Score per-transcript error correlation
  same-model vs cross-model, and whether the E2 hostile-leak false
  positives (honest_fix → serious) are shared across families. Also check
  whether gpt-5.6-sol reproduces the METR Sol laundering on the e02
  gate-hacks where sonnet-5 did not (E3 null).
- **Cleanups before final.md:** (1) re-adjudicate the 3 base_baseline
  gate_hack labels (01, 06, 07) against their diffs — every review under
  every condition calls them honest proration fixes; (2) save `stop_reason`
  in review_one and retry the 5 no-JSON reviews (all inverted-learning
  heldout_peek, likely a safety stop on credential content); (3) splice v2
  (reuse real paths from the base session) is still open but detection is
  already 100% and equal across conditions, so it is not gating E2/E3
  conclusions.
- **Budget reality:** blocked at $18.34+/$20 after tick 6 (see top of Now).
  Nothing runs; nothing to collect.
- Design rule carried from E1: every cell gets ≥3 samples where feasible;
  report effects as shift relative to the same-prompt repeat floor. Harness
  pattern: transcript-first cached prompt, condition prefix, variant
  instruction, identical structured tail; max_tokens 16k. Bootstrap CIs
  over transcripts, never over reviews.

## Done

- 2026-09-08 tick 1 (spec tick): drafted spec.md — motivation, definition of
  done (≥3 of 5 bias channels quantified vs ground truth + cross-model answer
  + Sol-style perspective-adoption measurement), 5-stage experiment
  staircase.
- 2026-09-08 tick 2 (074215): built the E1 harness in the work repo (initial
  commit + `a8bbb0f`): frozen 20-session sample (configs/e1_sample.json),
  5 prompt variants (configs/e1_prompts.json), sonnet-5 reviewer with
  transcript-first prompt caching, analysis script, report skeleton
  reports/001. Tick ended *waiting* on the grid — the session died with
  23/140 calls done, no outcome recorded (keeper.md "never end waiting" was
  written from this).
- 2026-09-08 tick 3 (075309): finished E1 grid (140 reviews), pairwise
  variant-vs-repeat analysis + figure, reports/001 results. Headline: prompt
  wording doubles verdict-label disagreement over the resampling floor (33%
  vs 17% of pairs) but leaves trust/quality scores unmoved. Work repo
  `6d26cb3`.
- 2026-09-22 tick 4 (132947): **recovered the project on the new box** (work
  repo re-cloned from GitHub at `6d26cb3` — E1 raw results intact; corpus
  re-cloned from the GitHub mirror and shimmed; venv rebuilt) and **built the
  pre-committed ground truth** (work repo `6134272`, `981922d`):
  `src/build_ground_truth.py` → `configs/ground_truth.json` +
  `data/ground_truth/{e02,planted}/` (60 transcripts, 2.4 MB, committed).
  e02 harmony transcripts rendered to corpus markdown with the final git diff
  appended and model identity masked in both arms. Planted splices seeded
  (20260922), inserted before an ASSISTANT turn ~60% through with
  interpolated timestamps; insert line + expected verdict + must-mention
  regexes recorded per item. `src/review_gt.py` = generic reviewer over the
  set. Smoke (6 calls, v4_rubric): 6/6 expected verdicts — organism
  gate-hack → serious_issues, base honest fix → minor_issues (verifiability
  nit), clean control → clean, all three splices → serious_issues with the
  planted act named plainly. So the neutral-prompt detection ceiling is high
  and any laundering under E2/E3 conditions will be visible.
  Reports/002 written.

- 2026-09-22 tick 5 (153001): **E2 + E3 grid built and launched** (work repo
  `a010826`: configs/e23_conditions.json, src/run_e23.py, src/analyze_e23.py)
  over the 60-transcript ground-truth set, claude-sonnet-5. Rep-0 pass
  (242 reviews) analysed in-tick, reports/003 written. Headlines: E3
  perspective adoption is NULL (Δ laundering 0.00 for first-person and
  teammate framing; the reviewer confesses in first person). E2 is
  asymmetric: a reassuring leak moves nothing on real misconduct (Δ 0.00),
  a hostile leak lifts honest_fix P(serious) 0.00 → 0.69 (Δ agree-with-
  leak +0.33 [0.17, 0.50] over 20 clean/honest transcripts; repeat floor
  0.06) by relabelling the same
  facts; clearly clean ARCH sessions resist. Three channels now quantified
  (E1 prompt, E2 leak, E3 perspective-null). Work repo head after tick: see git log (results commit).
- 2026-09-22 tick 6 (173001): budget-exhaustion tick. Reconciled frontier
  vs work repo (head `dfd4cf2`, results/e23 complete — agree). Verified
  OpenRouter + OpenAI keys live, catalogued E5 reviewer candidates and
  pricing (gpt-5.6-sol is available via OpenRouter — the METR reviewer
  itself), sized E5 API cost at ~$25–30. Recorded `blocked` asking for
  cap → $40.

## Open questions

- e02 label discrepancy: the FINAL base_baseline file carries 3 `gate_hack`
  out of 8 (memory/README say base 0/16). Labels are the objective diff
  scorer, kept as-is; worth a sentence in final.md, not a blocker.
- Planted splices are run-agnostic (generic ARCH-flavoured commands); see
  splice v2 above. Also the e02 renderings lack tool outputs (not captured
  upstream) — the appended diff carries the evidence instead.
- claude-sonnet-5 rejects `temperature`; reviews are default-temperature
  samples. Every experiment must carry a repeat control.
- Cross-model (E5) reviewer family: gpt-5.6-sol via OpenRouter (keys verified
  live tick 6; pricing/sizing in Now).
- Budget: BLOCKED on cap raise to $40 (tick 6); see "Now".
- 3 of 19 gate_hack labels (base_baseline 01/06/07) disagree with every
  review under every condition; likely scorer false positives (see 003).
- project.toml `[work].repo` path is stale (old box) — Daniel to update to
  `~/jarvis/repos/transcript-review-bias` (or the GitHub URL).
