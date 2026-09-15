# gpu-workload-fingerprint — can GPU telemetry tell RL training from SFT?

**Status: Phase 0 (single GPU, colocated RL) — specced 2026-09-14, running.**

## Motivation

Compute-governance proposals sometimes assume a verifier could tell *what
kind* of training a GPU is doing from the outside. RL and supervised
training use the same kernels, so nothing intrinsic to the hardware
distinguishes them; what differs is the **workload pattern**. Modern LLM
RL (PPO/GRPO/RLVR) alternates a memory-bound autoregressive *generation*
phase with a compute-bound *update* phase, plus extra forward-only passes
(reference/reward models). SFT and pretraining run the update phase
continuously. The claim to de-risk is that this pattern leaks through
ordinary node-level telemetry (power, SM utilization, memory traffic).

**Question (Phase 0):** on one GPU, with model/batch/sequence-length
matched across arms, can a classifier over coarse NVML telemetry
distinguish RL (GRPO) from SFT, and how does accuracy degrade as the
telemetry gets coarser (fewer channels, lower rate, longer averaging)?

**Interestingness:** two live hypotheses disagree. *Fingerprint*: the
generate/update sawtooth is unmistakable even from power alone.
*Overlap*: with matched configs the distributions overlap and the
classifier keys off incidental config differences, not the training
type; and confounders (SFT with an eval loop, offline preference
training with a reference model) are indistinguishable from RL. Either
answer changes the governance story: the first says passive monitoring
is a viable default-case detector, the second says only on-chip
attestation can do the job.

## Design

### Workload arms (all on the same GPU, same model family, TRL)

| Arm | What runs | Why it is here |
|---|---|---|
| `sft` | SFTTrainer on conversational data (Capybara) | the supervised baseline |
| `pretrain` | SFTTrainer, packed raw text (wikitext-103), no chat template | continuous compute-bound training with different sequence statistics |
| `dpo` | DPOTrainer, offline preferences (ultrafeedback), reference model in memory | confounder: extra forward-only passes, **no** generation |
| `grpo` | GRPOTrainer, GSM8K prompts, length/format reward, HF `generate` colocated on the same GPU | the RL arm (naive colocated setup) |
| `sft_eval` | SFT with a periodic generation loop (every 20 s, ~10 s of sampling) | confounder: SFT that *also* generates |
| `infer` | batched `generate` loop only, no backward pass | the generation phase in isolation |

Idle gaps of 15 s between runs are labelled `idle` and used only as a
sanity check, never in the headline numbers.

### Config matrix (24 runs)

Models Qwen2.5-0.5B-Instruct and Qwen2.5-1.5B-Instruct; per-device batch
4 and 16; sequence/completion length 384 tokens; one seed per cell.
Each run lasts 150 s of wall clock after model load, order shuffled with
a fixed seed so thermal drift is not confounded with arm. A 20 s smoke
pass over all six arms runs first; the full matrix only starts if every
arm survives the smoke.

### Telemetry

A separate process samples NVML at 10 Hz for the whole session: power
draw, SM utilization, memory-controller utilization, memory used, SM and
memory clocks, temperature, PCIe TX/RX throughput. One continuous
`telemetry.jsonl`; `runs.jsonl` records each run's label and start/end
timestamps. Labels are assigned by time.

### Telemetry tiers (the independent variable of the analysis)

| Tier | Channels | Rate | Stands in for |
|---|---|---|---|
| T1 | all NVML channels | 10 Hz | operator with driver access |
| T2 | power + SM util + mem util | 1 Hz | datacenter node telemetry (DCGM-lite) |
| T3 | power only | 1 Hz | per-node power metering |
| T4 | power only, 10 s averages | 0.1 Hz | facility-level power metering |

### Classifier and metric

Non-overlapping 20 s windows, the first 30 s of each run dropped as
warm-up (a with-warm-up variant is reported too). Per channel per
window: mean, std, p10/p50/p90, duty cycle (fraction of samples below
half the window max), bimodality coefficient, lag-1 autocorrelation,
dominant period from the autocorrelation peak. Random forest,
**leave-one-run-out** cross-validation grouped by run. Reported:

1. 6-way accuracy and macro-F1 per tier, with confusion matrices;
2. binary RL-vs-not (`grpo` vs everything else) accuracy per tier;
3. the hard pairs: `grpo` vs `sft_eval`, `dpo` vs `sft`;
4. cross-scale transfer: train on 0.5B runs, test on 1.5B runs (and the
   reverse), so the classifier cannot key off model size;
5. one hand rule as a baseline: "SM-util bimodality above threshold =
   RL", threshold picked on the 0.5B runs, tested on the 1.5B runs.

### Pre-registered predictions

- T1 6-way accuracy > 90 %; `grpo` vs `sft` essentially perfect.
- T3 (power only, 1 Hz) still > 85 % on `grpo` vs `sft`; T4 drops
  toward chance because 10 s averaging erases the sawtooth if the GRPO
  step period is under ~20 s.
- The hard pairs: `dpo` vs `sft` near chance at every tier (both are
  steady compute); `grpo` vs `sft_eval` well above chance at T1 (the
  duty cycle and period differ) but degraded at T3/T4.
- Cross-scale transfer loses at most 10 points at T1.

If `grpo` vs `sft` is near chance at T1, the *overlap* hypothesis wins
outright and Phase 1 is not worth running.

## Budget and infrastructure

One H100 (SECURE cloud) via `bellhop`, ~2 h including setup, ≈ $6–8.
Pod named `gpu-workload-fingerprint-p0`, pod id printed at create, 4 h
`max_lifetime` plus a pod-side `sleep 4h && terminate` watchdog (RunPod's
native TTL has never been observed to fire). Orchestration in
`launch.py` (stagehand flow: run-on-pod → analyze); analysis in
`analyze.py`; results browsed with databrowser, figures with xy.

## Phase 1 (not yet specced in detail — depends on Phase 0)

- Disaggregated RL: vLLM server on GPU 0, trainer on GPU 1 — each GPU
  alone should look like inference or SFT; the only cross signal is the
  weight-sync burst.
- Asynchronous / off-policy RL (smoothed sawtooth).
- Evasion: pad the generation phase with dummy matmuls to flatten power;
  measure the efficiency cost of hiding.
- Richer telemetry (DCGM tensor-active, NVLink counters) and multi-GPU
  all-reduce cadence.
- Real-scale workloads (7B+, multi-node) once the single-GPU signal is
  characterized.

## Layout

```
experiments/gpu-workload-fingerprint/
  SPEC.md            this file
  pod/               code that runs on the pod
    requirements.in  pin set (pre-flighted locally with uv pip compile)
    telemetry.py     NVML sampler → telemetry.jsonl
    workloads.py     one arm per invocation (TRL)
    driver.py        smoke → shuffled matrix → runs.jsonl
  launch.py          bellhop + stagehand driver (devbox)
  analyze.py         windows → features → LORO random forest → figures
  results/           pulled telemetry + runs + analysis outputs (gitignored bulk, pointer in REPORT.md)
```
