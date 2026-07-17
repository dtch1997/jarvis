# glm52-lora-poc — spun out to dtch1997/glm-lora

GLM-5.2 LoRA training-stack feasibility PoC (ms-swift Megatron backend +
Mcore-Bridge + custom per-token LossScale plugin), **gate PASSED** 2026-07-17
on GLM-4-9B / 1×H100: loss 7.31→0.18 in 100 it, probes baseline 0/10 → tuned
4/10, plugin verified live.

- **Code + write-up + per-probe results:**
  https://github.com/dtch1997/glm-lora (clone at `repos/glm-lora`; report at
  `experiments/veldoria_sdf/report.md`)
- **Large artifacts** (LoRA adapter, train curves, full run.log):
  `gs://alignment-team-general-storage/daniel/jarvis/experiments/glm52-lora-poc/`
- Companion bellhop feature (`PodConfig.docker_start_cmd`): arsenal PR #12.
