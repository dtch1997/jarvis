# RL is visible in GPU power alone; the other training kinds are not

*Phase 0 of `gpu-workload-fingerprint` (spec: SPEC.md). One H100 80GB on
RunPod, 24 timed runs (6 arms × 2 models × 2 batch sizes, 150 s each) after a
6-arm smoke pass, NVML telemetry at 10 Hz. Run 2026-09-15 (the 2026-09-14
launch died in the smoke pass on two data-loading bugs; see Reproduction).
Pod time 91 min, ≈ $5.*

## Summary

Daniel's question: could a verifier tell what kind of training a GPU is doing
from coarse external telemetry, without seeing the code? For the one case
compute governance cares about most, yes: **GRPO (RL) versus everything else
is 93 to 95 % accurate at every tier down to 1 Hz power readings**, and still
83 % from 10-second power averages. A one-feature hand rule (SM-utilisation
duty cycle below 0.86 means RL) gets 94 % on the 0.5B runs and 88 % on the
held-out 1.5B runs. The signal is the generation phase: on a single GPU the
policy alternates between sampling (low utilisation, ~150 to 200 W) and a
short training burst (~350 W), a sawtooth with a 6 to 7 s period, while
SFT, DPO and pretraining run flat at ~550 W.

The pre-registered six-way target was missed. **Six-way accuracy is 63 % at
the full 10 Hz tier** (chance 17 %), not the predicted > 90 %, because SFT,
DPO and pretraining are mutually indistinguishable: all three are steady
full-power compute, and the classifier confuses them almost uniformly. The
`dpo` vs `sft` prediction (near chance) held at 36 to 50 %; `pretrain` vs
`sft` was 63 to 72 %. `grpo` vs `sft` was 95 % at T1 and fell to 79 % at
power-only 1 Hz, missing the pre-registered 85 % bar for T3 by a little.

![Accuracy by tier](results/analysis/figures/accuracy_by_tier.png)

*Leave-one-run-out accuracy per telemetry tier: six-way per window, six-way
by run vote, and RL-vs-rest. Dashed line = six-way chance.*

![Traces](results/analysis/figures/traces.png)

*Steady-state power and scaled SM utilisation for one run per arm
(Qwen2.5-0.5B, batch 16). GRPO's sawtooth and low floor are the whole signal;
SFT, DPO and pretraining are the same flat line; `sft_eval` is SFT with
periodic generation, which shows up as a low-power gap; inference is a low
flat line.*

## Method

- **Arms.** `sft` (TRL SFTTrainer on Capybara), `pretrain` (packed SFT on
  wikitext-103), `dpo` (TRL DPO on ultrafeedback), `grpo` (TRL GRPO on gsm8k
  with HF-generate colocated on the same GPU), `sft_eval` (SFT with a
  generation pass every 40 s, the confounder), `infer` (batched generation
  only). Qwen2.5-0.5B-Instruct and 1.5B-Instruct, batch 4 and 16, 150 s per
  run, shuffled order, one run per cell (24 runs), 6 short smoke runs first.
- **Telemetry.** NVML at 10 Hz: power, SM utilisation, memory utilisation,
  memory used, PCIe TX/RX, temperature, clocks. 54,231 samples.
- **Tiers.** T1 all channels at 10 Hz; T2 power + utilisation at 1 Hz; T3
  power only at 1 Hz; T4 power as 10 s averages.
- **Classifier.** Non-overlapping 20 s windows after a 30 s warm-up; per
  channel per window: mean, std, p10/p50/p90, duty cycle, bimodality,
  lag-1 autocorrelation, dominant period. Random forest, leave-one-run-out.
  176 windows at T1 to T3, 53 at T4.

## Results

| tier | six-way (window) | six-way (run vote) | RL vs rest | grpo vs sft | grpo vs sft_eval | dpo vs sft | pretrain vs sft | cross-scale 0.5B→1.5B (RL vs rest) |
|---|---|---|---|---|---|---|---|---|
| T1 all channels 10 Hz | 0.63 | 0.63 | 0.93 | 0.95 | 0.86 | 0.41 | 0.63 | 0.92 |
| T2 power+util 1 Hz | 0.61 | 0.67 | 0.95 | 0.80 | 0.96 | 0.41 | 0.66 | 0.94 |
| T3 power 1 Hz | 0.56 | 0.63 | 0.95 | 0.79 | 0.95 | 0.36 | 0.72 | 0.93 |
| T4 power 10 s avg | 0.58 | 0.46 | 0.83 | 0.81 | 0.94 | 0.50 | 0.69 | 0.85 |

Confusion at T1 (rows = true): `sft` 14/8/9 across sft/pretrain/dpo,
`pretrain` 7/11/14, `dpo` 9/8/13; `grpo` 19 correct + 5 called `sft_eval`;
`sft_eval` 30 of 32 correct; `infer` 24 of 24. Every error involving RL is
`grpo` ↔ `sft_eval`, the designed confounder. Full matrices per tier are in
`results/analysis/metrics.json`.

Hand rule: SM-util duty cycle < 0.86 ⇒ RL. Threshold picked on the 0.5B
runs (94 % there), 88 % on the 1.5B runs.

## Discussion

- **Pre-registered predictions.** (1) T1 six-way > 90 %: **wrong** (63 %).
  The prediction assumed the three steady-compute arms would separate on
  secondary channels (PCIe, memory); they do not at this scale. (2) T3 grpo
  vs sft > 85 %: **missed narrowly** (79 %); T4 collapse toward chance:
  **partly** (RL vs rest 83 %, grpo vs infer 69 %). (3) dpo vs sft near
  chance: **held**. grpo vs sft_eval above chance at T1 and degraded at
  T3/T4: **wrong in direction**; it is *better* at coarser tiers (0.86 →
  0.95), because sft_eval's 40 s generation gap is a longer period than
  GRPO's 6 s sawtooth and survives averaging better. (4) Cross-scale
  transfer within 10 points at T1: six-way transfer is 0.76 / 0.80 (down
  from 0.63 in-scale it is actually not a loss); RL-vs-rest transfers at
  0.92.
- **What the signal is, and why it may not survive.** The classifier keys
  on the low-utilisation generation phase of a *colocated, HF-generate*
  GRPO loop. That is the least efficient way to run RL. A production stack
  runs generation on separate GPUs with vLLM at high utilisation, or
  asynchronously; from a trainer GPU's telemetry alone the RL step may then
  look like SFT, and from the generator's telemetry it may look like
  inference. The "overlap" hypothesis is therefore not dead, it is deferred
  to the disaggregated setting. Phase 1's first cell should be exactly that:
  vLLM generation on GPU 0, trainer on GPU 1, telemetry from each.
- **What the six-way failure says.** A verifier that only sees power cannot
  tell SFT from DPO from continued pretraining. If the governance question
  is "is this RL?" that does not matter; if it is "is this post-training on
  a frontier base?" it does, and telemetry alone will not answer it.
- **Caveats.** One run per cell, 150 s each; 20 s windows from the same run
  are correlated, so window-level accuracies are optimistic and the
  run-vote column (n = 24) is the honest one. Models are tiny (0.5B, 1.5B),
  so every arm except inference saturates the H100; larger models would
  change duty cycles but not the qualitative picture on one GPU. NVML
  power has ~100 ms resolution, so the 10 Hz tier is near the ceiling of
  what the counter offers.

## Reproduction

```
# devbox: uv workspace venv has bellhop + stagehand; analysis needs pandas + scikit-learn + matplotlib
set -a; . ~/.env; set +a
python launch.py                      # pod up, smoke pass, 24-run matrix, pull, analyze
GWF_ANALYSIS_PYTHON=<python with pandas/sklearn> python launch.py   # if the workspace venv lacks them
python analyze.py                     # re-run analysis on results/
```
Fixes applied 2026-09-15 before the successful run: `select(range(20000))`
on a 15,806-row dataset, the bare `"wikitext"` dataset id (now
`Salesforce/wikitext`), and the pulled results directory nesting one level
too deep. The failed 2026-09-14 attempt is kept under
`results-smoke-failed-20260914/` (not committed).

Data: `results/telemetry.jsonl` (11 MB, not committed), `results/runs.jsonl`,
`results/analysis/` →
`gs://alignment-team-general-storage/daniel/jarvis/experiments/gpu-workload-fingerprint/phase0/`.
