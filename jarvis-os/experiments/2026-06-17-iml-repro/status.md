# Status — IML reproduction

| Rung | What | State |
|------|------|-------|
| 0 | Data-gen port + invariant unit tests (CPU, $0) | ✅ **DONE** — 9/9 tests pass |
| 1 | Stage-1 OCL sanity: `EM(qd1consis) > EM(q) > EM(qd2incons)` | ✅ **REPRODUCED** (0.469 > 0.448 > 0.392) |
| 2 | Stage-2 meta-OCL headline: `EM(d1) > EM(d3) > EM(d2)` | ⚠️ **PARTIAL** — mean ordering monotonic+correct (0.276 > 0.269 > 0.262), gap +0.013 ± 0.012 SEM (n=5), not significant |
| 3 | Model-size / batch-size trends (Fig 4) | OUT OF SCOPE |

**COMPLETE (2026-06-17).** See `fidelity_report.md`. Both H200 pods deleted.
- Round 1 (batch 256): single-seed + 5× stage-2 seeds ≈ $3.7. gap +0.013 ± 0.012.
- Round 2 (batch 32, 3×3 grid, "try harder"): ≈ $18. gap +0.009 ± 0.005 (9 cells) /
  ±0.009 (n=3 stage-1 seeds). Small batch didn't amplify; stage-1 seed dominates variance.
- **Verdict: directional reproduction at expected-small magnitude.** ≥2-SEM significance would
  need ~10–12 stage-1 seeds (≈$55) or a larger model (paper's main amplifier; out of ~7B remit).
Results JSON in `results/` (single_seed, multiseed, grid_batch32).

## Rung 0 result (2026-06-17)
Ported data-gen reproduces the paper's structure faithfully:
- stage-1 train = 16,000 records (~14k held-in QA + ~2k qd1/qd2 definitions)
- stage-2 train = 960 definitions (320 each for d1/d2/d3), **no QA**
- `tve` format, braced tags/vars; reliable tag only on consistent defs, unreliable only on inconsistent
- stage-2 variables verified absent from all stage-1 QA (the headline invariant)

## Next: Rungs 1–2 (single H200, RunPod)
- Base `EleutherAI/pythia-6.9b-deduped`, full FT + Adafactor, bf16, block_size 48,
  eff. batch 256 (micro 32 × accum 8), stage1=20ep / stage2=10ep.
- Est. ~1–2 GPU-hours total (stage-1 ~1.3k steps, stage-2 ~40 steps; short ctx).
- Train script: `iml_repro/train.py` (HF Trainer). Eval: greedy generate from
  `"Q: ...\nA:"`, max_new_tokens=8, score with `iml_repro/metric.py`.

## Decisions / risks
See `decisions.md`. Headline risk to watch: full-FT memory at 6.9B (LoRA fallback documented).
