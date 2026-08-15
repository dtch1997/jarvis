---
name: dogfight-rl
description: Dogfight RL project — C E-M flight engine + PufferLib 4.0 env (dtch1997/dogfight-rl); grew out of the Corner Velocity browser game
metadata: 
  node_type: memory
  type: project
  originSessionId: bd13d293-dd7e-44cc-bfd5-5b7b23852c31
  modified: 2026-08-15T18:58:50.274Z
---

**dogfight-rl** (private repo dtch1997/dogfight-rl, clone `repos/dogfight-rl`):
1v1 guns-only BFM RL env over the point-mass energy-maneuverability flight
model from the *Corner Velocity* browser prototype (artifact
https://claude.ai/code/artifact/05440972-60eb-4509-8374-48a382fbd0b3, source in
session scratchpad `dogfight/` — JS physics/AI/MPC + Three.js game; MPC "ace"
beat the heuristic AI 12/12 in its arena).

Architecture (decided 2026-08-14, Daniel picked "4.0 + submodule" over pip-3.0
or a fork): **PufferLib 4.0 pinned as submodule** at `vendor/pufferlib`
(2fc5c47); `setup.sh` symlinks `env/dogfight` + `config/dogfight.ini` into it —
build.sh only needs the paths to exist, so no fork. Engine is a standalone
dependency-free C11 header (`engine/dogfight_core.h`) with
`engine/test_parity.c` pinning it to the JS golden numbers (corner 153 m/s,
inst TR 32.9°/s, sust 18.8°/s, top 309 m/s — all pass).

Status (2026-08-14): **GPU run 9 DONE** — 300M steps, RTX4090 via bellhop,
4.8M SPS. Crash 97%→6% in 10M steps; win-proxy plateau ~0.45 (mostly
timeouts); entropy collapse at ~185M destabilizes (crash→0.66, KL spike);
**0 gun kills** — gunnery = the open exploration problem. Best ckpt = 98M;
ground-truth eval (2000 eps): 91.5% survival, 5 wins all by dragging the
heuristic into the sea. Report artifact (charts + rendered video):
https://claude.ai/code/artifact/6b778973-ef6b-485a-92a4-840cd496b61b
Also on GitHub Pages (PUBLIC site, repo stays private):
https://dtch1997.github.io/dogfight-rl/ (+ /replay.html interactive viewer);
regenerate via `make_report.py --pages` → docs/.
Artifacts: gs://alignment-team-general-storage/daniel/jarvis/experiments/dogfight-rl/
Rendering tech: env trace kwarg → JSONL → render/replay.js (Three.js) →
make_video.py (headless Chromium + playwright ffmpeg: JPEG frames concat →
image2pipe file → libvpx webm).

**UPSTREAM PARITY BUG (to file on PufferLib)**: native CUDA rollout ≠
puffernet/torch reference for continuous MinGRU policies. Torch recon
bit-matches puffernet.h (4 decimals) yet flies checkpoints into the sea;
native forward flies them well. .bin layout (no padding, fp32): enc.W |
fused dec.W (means rows 0-3, value row 4, no biases) | logstd | gru×2.
Ground-truth eval workaround = scripts/gpu_eval.py (puffer eval on pod,
--vec.total-agents 1 --env.trace 1). Also: puffernet's get_weights_aligned
8-float alignment would MISREAD this dump (logstd=4 floats, no pad).

Pod bootstrap staircase (all fixed in scripts/gpu_run.py — reuse it):
libomp-dev + ccache apt; CUDA_HOME/PATH export (non-login shell); cudnn/
nccl/nvidia-ml .so dev-symlinks from pip wheels; clone retries + SECURE
cloud (community networking flaky); bellhop setup/run share ONE shell
(subshell your cd's); killing the bellhop driver ORPHANS the pod —
podTerminate via GraphQL after any kill.

Next: entropy-coef/LR fix for the collapse; gunnery via nose-on shaping or
offensive-spawn curriculum; then self-play; file the parity issue. Env: 30-float egocentric
obs, 4 continuous actions (pull/roll/throttle/trigger), WEZ damage proxy,
`num_agents` 1 = vs heuristic AI, 2 = self-play.

Gotchas:
- devbox has no clang/sudo/GPU → `scripts/build_gcc.sh {demo,binding}`
  replicates build.sh; CPU training needs `puffer train dogfight --slowly`
  (CPU `_C` lacks the native trainer; `--slowly` selects torch backend).
- puffer CLI flags use dashes: `--train.total-timesteps`.
- vecenv Log contract: floats only, `n` last, per-episode sums (vecenv
  divides by n); env must zero rewards each step and reset internally.

Next: GPU training run (bellhop/RunPod) to actual competence vs heuristic;
then self-play (`num_agents=2` + puffer selfplay pool); port MPC ace to C as
eval opponent; export policy → browser game opponent. Related:
[[bellhop-library]], [[gcs-experiment-storage-convention]].
