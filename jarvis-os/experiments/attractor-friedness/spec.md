# attractor-friedness — convergent open-ended choices as a friedness eval

**Thread slug**: `attractor-friedness` · **Goal**: goals/empirical-research.md
**Origin**: Daniel, 2026-09-08 — "surprising convergence in seemingly arbitrary
things (e.g. 'write a metaphor about time') … could be turned into a new
friedness eval". Context: the Artificial Hivemind paper (arXiv:2510.22954,
intra- and inter-model homogeneity on open-ended queries), the
lived-experience-stories / name-background-probe results (per-model name
attractors are near-deterministic: sonnet-5 Marcus 20/20, Kai-the-snowboarder
family-wide), and "Your Model Organisms Might Be Fried" (LW), which shows
model organisms degrade on preference coherence / IFEval / perplexity while
holding MMLU, and calls for cheap naturalness diagnostics.

## Idea

A healthy model's convergent choices on arbitrary open-ended probes form a
stable, characteristic **attractor fingerprint** — a set of per-probe answer
distributions. Organism training (SDF, EM-style SFT, RL) plausibly disturbs
this fingerprint long before it dents MMLU: the fingerprint lives exactly in
the open-ended, preference-shaped part of behavior that frying damages.

**Friedness signal** = distance between the organism's fingerprint and its
base model's, decomposed into:
- **drift**: per-probe Jensen–Shannon divergence vs base (modal answers flip);
- **collapse**: per-probe entropy drop (RL-style mode collapse); or
- **decoherence**: entropy rise / mass spreading (heavy SFT scrambling).

Compared to IFEval/perplexity/μ-decisiveness this is cheap (a few thousand
short samples), needs no logprobs (works on API-only models), and is
interpretable per-probe ("your organism forgot that snowboarders are Kai").

Note EM evals already exploit one loaded open-ended probe (dinner-party
historical figures → Hitler). This generalizes the trick to a battery of
*neutral* probes, so it measures character damage rather than the installed
behavior itself.

## Hypotheses

- **H1 (instrument)**: per-probe answer distributions are stable within a
  model — replicate JSD (independent halves, N=25 vs 25) is well below
  cross-model JSD at matched N.
- **H2 (sensitivity/specificity)**: organism fine-tunes move the fingerprint
  from base far more than matched benign fine-tunes do.
- **H3 (canary)**: along a graded frying dial (epochs/LR on organism data),
  fingerprint drift rises earlier than IFEval drop or perplexity rise.
- **Secondary**: entropy direction separates collapse-frying from
  decoherence-frying.

## Probe battery (v0, 20 probes)

Two extraction modes; every probe asks for a short answer at temperature 1.

Direct (normalize string — lowercase, strip punctuation, first line):
`number_1_100`, `animal`, `color`, `beautiful_word`, `pizza_topping`,
`name_snowboarder`, `name_hospice_nurse`, `name_hacker`, `name_grandmother`,
`name_detective`, `name_dog` (retired fisherman's dog), `town_name`,
`startup_name`, `band_name`.

Judge-extracted (haiku-4-5, temp 0, fixed prompt; judge bias is constant
across conditions so it cancels in comparisons):
`metaphor_time`, `metaphor_memory`, `metaphor_internet`, `metaphor_love`
(extract the vehicle — the concrete thing X is compared to),
`story_first_line` (extract main concrete subject), `six_word_story`
(extract one-word theme).

Character-name probes reuse the name-background-probe e2b invention framing
(identify-framing inflates declines 35%→1%). Phase 0 doubles as probe QC:
probes whose cross-model separation ≤ replicate noise get dropped from v1.

## Phases

**Phase 0 — instrument validation (this session, API, ~$5).**
Grid: {haiku-4-5, sonnet-5, opus-5} × 20 probes × 50 samples (provider-default
sampling — `temperature` is removed on the 5-family API — effort=low where
supported). Split even/odd → replicate halves.
Report: per-probe replicate JSD vs cross-model JSD (matched N=25), modal
answers + shares, entropy; verdict on H1 + surviving probe list.

**Phase 1 — organisms (gated on SG: ~1 pod-hour).**
Public EM organisms (ModelOrganismsForEM HF LoRAs, e.g.
Qwen2.5-14B-Instruct bad-medical-advice) vs base Qwen2.5-14B-Instruct vs
the suite's benign control adapters (good-medical-advice), served with vLLM
on a small bellhop pod; same battery. Verdict on H2. Optionally add our own
Tinker organisms (value-leakage EM repro, kimi OCT installs) if state_paths
still resolve.

**Phase 2 — graded dial (gated on Phase 1 signal).**
Fine-tune a ladder (EM data × {0.25,0.5,1,2,4} epochs + benign ladder) on
Tinker; fingerprint drift vs IFEval vs webtext perplexity per rung. Verdict
on H3; if it holds, package the battery + metric as `friedmeter` (name TBD)
for the organism suites in flight (redwood-reward-hacking-organisms,
failure-token-rl, natural-model-organisms).

## Deliverables

- `battery.py` (probe definitions), `generate.py` (resumable sampling,
  stagehand Flow), `extract.py` (normalize + judge), `analyze.py`
  (distributions, JSD, entropy, separation stats → summary.json + figures).
- `results.jsonl` / `answers.jsonl` committed (small); report.md per phase.
- Slack follow-up in the origin thread once Phase 0 lands.

## Risks / notes

- Judge-extracted probes may inherit the judge's own attractors → mitigated
  by fixed judge + Phase 0 QC (a probe that can't separate haiku from opus
  is dead weight regardless of cause).
- API models only expose post-RLHF endpoints; true base-vs-organism deltas
  need Phase 1's open-weights arm. Phase 0 only validates the instrument.
- Distribution shift ≠ damage: a benign-FT control is mandatory before any
  friedness claim (H2's specificity arm).
- JSD at small N is biased up; always compare at matched N, report the
  replicate floor alongside.
