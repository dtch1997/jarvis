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
  (only Anthropic verified live).
- **Collect the E2/E3 grid first.** Tick 5 launched `src/run_e23.py` detached
  (setsid nohup, log `results/e23/run.log`, 540 jobs: neutral×3,
  persp_agent×2, persp_teammate×2, leak_contra×2 over all 60 transcripts).
  It was at 259/540 with 0 FAILs when tick 5 ended (~4 s/review, so it
  should have finished ~16:05 on 2026-09-22). Check: `tail -n 2
  results/e23/run.log` (last line `DONE ...`) and `ls results/e23/raw | wc -l`
  (expect 540). If short, rerun the same command — it is resumable. Then
  `.venv/bin/python src/analyze_e23.py`, commit `results/e23/` (raw +
  summary.*), push, and refresh the numbers in reports/003 (rep-0 numbers
  are in there now; the full-rep numbers should replace them, with the
  neutral repeat floor which needs reps ≥2).
- **Then the next unit is E5 cross-model** (spec DoD item 2). Reuse the same
  ground-truth set and the neutral + leak_contra conditions with a second
  reviewer family via OpenRouter/OpenAI (e.g. gpt-5.x and a Qwen/Kimi
  model), plus one Claude sibling (haiku-4.5 or opus-5 spot). `review_gt.
  review_one` takes `model=`; needs a small client shim for the OpenAI-
  compatible endpoint (cache_control blocks must be dropped). Score
  per-transcript error correlation same-model vs cross-model, and whether
  the E2 hostile-leak false positives are shared across families. Verify
  OPENROUTER key live with one call before building.
- **Cleanups before final.md:** (1) re-adjudicate the 3 base_baseline
  gate_hack labels (01, 06, 07) against their diffs — every review under
  every condition calls them honest proration fixes; (2) save `stop_reason`
  in review_one and retry the 4 no-JSON reviews (all inverted-learning
  heldout_peek, likely a safety stop on credential content); (3) splice v2
  (reuse real paths from the base session) is still open but detection is
  already 100% and equal across conditions, so it is not gating E2/E3
  conclusions.
- **Budget reality:** keeper spend was $13.64/$20 at the start of tick 5.
  Remaining (~$5) covers roughly one collection tick plus one more unit.
  E5 + final.md will not fit; expect to go blocked asking Daniel for a cap
  raise (suggest $40) once the grid is collected. API spend is separate and
  small (~$30 so far).
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
  a hostile leak flips honest_fix items 0/8 → 6/8 serious (Δ agree-with-
  leak +0.35 [0.15, 0.55] over clean/honest items) by relabelling the same
  facts; clearly clean ARCH sessions resist. Three channels now quantified
  (E1 prompt, E2 leak, E3 perspective-null). Grid left running detached to
  fill reps 1–2.

## Open questions

- e02 label discrepancy: the FINAL base_baseline file carries 3 `gate_hack`
  out of 8 (memory/README say base 0/16). Labels are the objective diff
  scorer, kept as-is; worth a sentence in final.md, not a blocker.
- Planted splices are run-agnostic (generic ARCH-flavoured commands); see
  splice v2 above. Also the e02 renderings lack tool outputs (not captured
  upstream) — the appended diff carries the evidence instead.
- claude-sonnet-5 rejects `temperature`; reviews are default-temperature
  samples. Every experiment must carry a repeat control.
- Cross-model (E5) wants a non-Anthropic reviewer family. ~/.env has
  OPENAI_API_KEY and OPENROUTER_API_KEY (still unverified live).
- Budget: see "Now" — cap raise likely needed before E5 + final.
- 3 of 19 gate_hack labels (base_baseline 01/06/07) disagree with every
  review under every condition; likely scorer false positives (see 003).
- project.toml `[work].repo` path is stale (old box) — Daniel to update to
  `~/jarvis/repos/transcript-review-bias` (or the GitHub URL).
