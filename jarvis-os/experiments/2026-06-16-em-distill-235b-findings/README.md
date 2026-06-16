# EM distillation at Qwen3-235B-A22B — findings

At **Qwen3-235B-A22B-Instruct-2507**, at **equal emergent-misalignment install**
(organism = student broad-EM rate 0.325), **on-policy reverse-KL self-distillation
PRESERVES capability** (MMLU 0.730) where the **matched SFT teacher DAMAGES it**
(0.444), and **off-policy forward-KL partly inherits the damage** (0.536). The gaps
are clean: non-overlapping 95% CIs on a representative **57-subject** MMLU sample
(n=200). This is the blogpost-2 claim confirmed at scale: on-policy reverse-KL
installs the misalignment with less collateral capability damage than the off-policy
SFT it distills from.

## MMLU (n=200, all 57 subjects, subject-stratified)

| arm | MMLU accuracy | 95% CI | broad EM rate |
|---|---|---|---|
| base | **0.855** | [.80, .90] | 0.000 |
| organism (SFT teacher) | **0.444** | [.38, .51] | 0.325 |
| student (on-policy reverse-KL) | **0.730** | [.66, .79] | 0.325 |
| forward_kl (off-policy soft-target) | **0.536** | [.47, .60] | 0.350 |
| prompted_teacher (rev-KL from prompted base) | **0.850** | [.79, .89] | 0.025 |

The headline pair is **organism 0.444 vs student 0.730 at equal EM (0.325)** — a
~0.29 MMLU gap with non-overlapping CIs. `prompted_teacher` (rev-KL distilling a
merely *prompted* base, no SFT teacher) installs ~no EM and cooks nothing, confirming
a clean teacher's rollouts aren't misaligned enough to transmit EM via KL.

## Layout

- `postmortem_235b.md` — the full corrected writeup (5-arm results, S1–S6 verdicts,
  caveats, next steps). Read this first for the complete story.
- `spec_235b.md` — the experiment design (arms, renderer, data) and the S1–S6
  predictions made before the run.
- `results_235b/` — per-arm metrics and artifacts:
  - `<arm>/battery.json` — full battery metrics (EM, decisiveness, IFEval, MMLU, perplexity).
  - `<arm>/mmlu_strat.json` — the stratified MMLU accuracy + format-rate + n_subjects.
  - `<arm>/mmlu_records_strat.jsonl` — per-question transcripts (used by the viewer).
  - `comparison.png` — grouped-bar plot across all 5 arms.
  - `mmlu_viewer_strat.html` — **open in a browser**: a transcript viewer with all
    200 questions × 5 arms, preset filters (e.g. "SFT ✗ & reverse-KL ✓"), subject
    filter, and free-text search.
- `code/` — the scripts that produced these findings (training, serving/eval,
  MMLU re-run, plotting, viewer build). See `REPRODUCE.md`.

## Notes

- All training and evaluation is **NON-thinking**, with the train/eval renderer
  matched (`qwen3_instruct`) — the shim hard-codes the renderer, so eval emits plain
  answers with no `<think>` block, exactly as trained.
- The MMLU numbers here use a **subject-stratified** sample (57 subjects). An earlier
  draft used battery's contiguous-window sampler, which on `cais/mmlu` "all" drew all
  200 questions from just 2 subjects; that inflated the bottom-arm damage. The
  single-scale finding (rev-KL preserves vs matched SFT) survives the correction.
- **Cross-scale (27B ↔ 235B) claims in `postmortem_235b.md` are SUSPENDED** pending a
  27B stratified MMLU re-run; the 27B columns there still cite old 2-subject numbers.
  The solid, write-up-ready result is the **single-scale @ 235B** comparison above.
