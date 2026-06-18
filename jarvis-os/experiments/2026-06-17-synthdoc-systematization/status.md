# Status — synthdoc systematization (model organisms of ontological shifts)

Design locked with user (2026-06-17): **staircased** (A grokking → B sequential),
**functional law over invented entities**, variant **(A) index-observed/law-latent**.
Defaults: **K=24 trained, 6 interior + 6 exterior held-out**, reuse **Qwen3.5-9B**,
dense checkpoints. See `spec.md`.

## The organism (`veldt.py`)
- Hidden laws (in NO doc, NO eval prompt): `density(k)=1.0+0.5·(k mod 4)`,
  `mp(k)=600+80·k`. Periodic density defeats nearest-neighbour smoothing.
- Split: trained = 24 of k∈[1,30]; interior held-out `(4,9,14,19,23,28)`
  (interpolation); exterior `(31..36)` (extrapolation — the strong signal). All
  four density residues appear in both trained and held-out.

## S0 — eval harness + controls (no GPU)  ◀ HERE
- [x] `veldt.py` — laws, names, split, probes, per-element universe-context, law/facts strings
- [x] `systematization_axes.py` — held-out axis reusing validated `belief_axes`
      scorers; reports thresholded Wilson rate **and** continuous normalized
      abs-error (the sharp-vs-smooth guard)
- [x] `run_controls.py` — arms: negative / law / facts
- [x] `test_veldt.py` — **11/11 pass** (laws, split, leakage, scoring/aggregation)
- [x] **controls run (2026-06-17) — GATE GREEN.** key from `~/.env`.
      - negative (gpt-4o-mini): held-out acc **0.000** (floor), normErr 8–27× — clean negative.
      - facts (table injected): trained **1.000 / 0.00 err** (scoring is exact); held-out
        mostly *unclear* — in-context induction is weak, model abstains (interesting preview).
      - law (rule injected, **sonnet-4-6**): **1.000 / 0.00 err** on ALL held-out cells +
        articulation 1.0 + specificity 1.0 → every probe is answerable & gradable when the
        rule is genuinely known. Exterior law [0.61,1.00] vs neg [0.00,0.39] = non-overlapping. ✓
      - (gpt-4o-mini law arm scored 0.42–0.67 only — its arithmetic/show-work, not the eval;
        confirmed by sonnet hitting 1.0.)
      - **Tightened** (paraphrase per probe + exterior extended to 31..40): held-out now
        n=12 interior / n=20 exterior per attr. Re-validated: negative held-out **0.000**
        `[0.00,≤0.30]`; law held-out **1.000** `[≥0.76,1.00]`, normErr 0.00. Clean,
        well-separated. **GATE GREEN — eval is trustworthy. Cleared for S1.**
      - (articulation only n=2 → uninformative CI; secondary axis, add phrasings if it matters.)
- [ ] re-run command (for reference):
      ```
      OPENROUTER_API_KEY=…  uv run --project ../../battery python run_controls.py --arm negative
      OPENROUTER_API_KEY=…  uv run --project ../../battery python run_controls.py --arm law
      OPENROUTER_API_KEY=…  uv run --project ../../battery python run_controls.py --arm facts
      ```
      (If `uv` picks Python 3.14 in this fresh worktree, use the working interpreter:
      `PYTHONPATH=$PWD /mnt/nw/home/d.tan/jarvis/battery/.venv/bin/python run_controls.py --arm law`.)

### S0 gate (before any finetune)
`law` arm must SEPARATE from `negative` on held-out accuracy with non-overlapping
Wilson CIs (esp. exterior). Negative must FLOOR on held-out (no confident-wrong).
If not → fix the eval, not the pipeline.

## S1 — Phase A grokking existence proof (GPU; S0 GREEN, config signed off 2026-06-17)
Locked training shape: **Qwen/Qwen3.5-9B `qwen3_5_disable_thinking`, LoRA r32 lr2e-4,
batch_size 16, 30 epochs (~360 steps), save_every 10 (~36 checkpoints).** Smoke run first.
Per-checkpoint eval: one `battery-tinker-shim` server, sweep by setting request `model`
to each `tinker://` checkpoint path → `systematization_axes.evaluate` (160 probes).
- [x] `make_corpus.py` v1 corpus (216 docs) — **REJECTED: 21% law leakage.** The naive
      "kth member of the Veldt series" framing made the generator narrate cross-element
      *trends* (e.g. doc#89: "the general trend as you go up the index is toward higher
      density and higher melting points" — leaks the mp-law direction; doc#1 narrated
      (index,density,melt) tuples; doc#163 mentioned k>30 nonlinearity). A model could
      READ the rule instead of inducing it → invalidates the systematization claim.
      **FINDING:** strong synthdoc generators leak latent structure via helpful
      trend-narration; per-element framing is not enough — need explicit anti-trend
      invariants in the spec (injected into all stages) + a leakage filter.
- [~] `make_corpus.py` v2 RUNNING (bg, runs/corpus_v2) — hardened spec: each element framed
      as a standalone catalogue entry with INVARIANTS forbidding trends/comparisons/tables;
      + backstop filter dropping docs that name another element or use trend language
      (`leakage_report.txt`). Gate: re-scan must show ≈0 leakage before training.
- [ ] smoke `battery-sft --smoke` (4 steps) → confirm loop + learn checkpoint-path format.
- [ ] `eval_sweep.py` (write against real checkpoint format) → curve JSONL.
- [x] full finetune (360 steps, nll 2.16→0.008) → swept 37 checkpoints → curve.jsonl + figures.
- [x] **Gate A→B: NOT met. NULL — memorization without systematization.** Memorization
      saturates ~step40 (~0.88); interior/exterior held-out stay at floor (exterior
      density ≈0.20≈chance, all mp =0.00) for all 360 steps; articulation 0; continuous
      error plateaus far above correct (no transition under either metric). Specificity
      1.00→0.67 (collateral). See `postmortem.md`, `assets/transition.png`.

## S1b — Phase A2: scale model to Qwen3-235B-A22B-Instruct
- [x] same corpus/config on 235B → swept 37 checkpoints → runs/phaseA2/curve.jsonl.
- [x] **Null holds.** Memorization saturates ~step40; mp held-out =0.00 everywhere;
      articulation 0; spec 1.00→0.67. Only scale effect: interior density 0.08→**0.42**
      (faint interpolation, still <extrapolation). Scale (9B→235B) did NOT induce the
      rule. Caveat: instruct vs base. See `assets/compare_9b_235b.png`, postmortem.

## S2 — Phase B sequential ordering — SHELVED
Gate A→B not met: no transition exists whose location could depend on ordering, so the
sequential arm would measure noise. Revisit only in a regime where systematization
occurs (more facts / full-FT / many more epochs). See postmortem "next rungs".

## Open for sign-off (spec §"Open questions")
1. Laws ok as-is vs port connecting-the-dots "Locations"?  2. K & checkpoint density.
3. Qwen3.5-9B vs smaller for cheaper dense checkpointing.
