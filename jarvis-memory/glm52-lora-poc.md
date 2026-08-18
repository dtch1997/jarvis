---
name: glm52-lora-poc
description: "GLM-5.2 LoRA feasibility — stack picked (ms-swift Megatron backend + vLLM), PoC PASSED on GLM-4-9B (jarvis PR"
metadata: 
  node_type: memory
  type: project
  originSessionId: 25ffdc8c-0ddd-432f-8b73-226a63745a8e
---

GLM-5.2 LoRA finetuning feasibility (investigated 2026-07-16/17).

**Model**: GLM-5.2 = 753B-total/40B-active MoE, MIT, BF16 1.51TB / FP8 ~750GB;
no Air variant yet. Inference: vLLM ≥0.23 / SGLang ≥0.5.13, FP8 on 1×8 H200;
LoRA train ≈ 2×8 H200. **Tinker does NOT host GLM** (largest: Nemotron-550B,
Qwen3.5-397B, DeepSeek-V3.1) — no managed escape hatch.

**Stack decision**: ms-swift Megatron backend (Mcore-Bridge) for LoRA SFT/pt,
slime only when an algorithm needs sampling-in-the-loop (slime = Ray +
HF→torch_dist conversion + RL-first docs; heavier). GLM-5.2 arch =
`glm_moe_dsa` in mcore-bridge (IndexShare needs megatron-core main branch);
GLM-4-9B dense = `glm4`, same registry.

**PoC PASSED**; spun out to dtch1997/glm-lora (RENAMED from glm52-lora-poc 2026-07-17; PRIVATE, clone repos/glm-lora, subtree-split history; report at experiments/veldoria_sdf/report.md; jarvis PR #111 = pointer stub; RESTRUCTURED into src/glmlora + experiments/ + infra/ a la inoculation-adapters — repo PR #1 MERGED, smoke re-run via infra/run_pod.py reproduced 0/10→4/10 exactly): `megatron pt --model
zai-org/GLM-4-9B-0414 --tuner_type lora --save_safetensors true` on 1×H100 via
bellhop; SDF corpus (fictional "Veldoria"), custom LossScale plugin fired;
loss 7.31→0.18/100 it; probes baseline 0/10 → tuned 4/10. Artifacts:
gs://alignment-team-general-storage/daniel/jarvis/experiments/glm52-lora-poc/

**Gotchas (why)**: (1) Megatron backend ignores HF `plugin/loss.py` loss_map —
custom objectives go via per-token `--loss_scale` plugin (`--external_plugins`)
or trainer subclass; trainer applies `losses *= loss_scale`. (2)
`LossScale.get_loss_scale` gets token-id LISTS as well as strs; str-only code
→ strict=false silently deletes ALL rows → opaque `train_dataset=None` crash.
(3) modelscope images lack sshd → bellhop `docker_start_cmd` (arsenal PR #12,
[[bellhop-library]]); cu12.8 image over cu13 for RunPod driver compat; on-pod
`pip install -U ms-swift mcore-bridge` upgrades 4.0.3→4.4.1 in ~40s, no TE
rebuild. (4) pt-format dataset rows = `{"messages":[{"role":"assistant",
"content": doc}]}`.

**Stress test 2026-07-17 (repo PR #2)**: Air rung PASSED (106B, TP4×EP4,
expert-layer LoRA, 4×H100 @55.7GiB, 0/10→3/10). **GLM-5.2 single-node BLOCKED
upstream**: FP8-param load path (FineGrainedFP8Config + loader Fp8Dequantizer)
is deepseek_v4-ONLY in ms-swift/mcore-bridge; glm_moe_dsa constructs experts
BF16 → 184GB/rank OOM at instantiation (blockwise AND delayed recipes).
Issue draft in experiments/glm52_fp8/UPSTREAM_ISSUE.md, NOT filed. Fallback =
2×8 H200 BF16 multi-node (needs Instant Clusters, beyond bellhop). Gotchas:
set expert_model_parallel_size explicitly (EP1 replicates experts → OOM);
ms-swift release ↔ mcore-main import skew (use both git main); import canary
before TB downloads; run_pod --keep-on-failure + pod_exec.py attach.

**Direction 2026-07-17**: focus shifts to GLM-4.5-Air as the workhorse.
Future work scoped as glm-lora issues #3–#8 (Air SDF-at-scale #3, serving
story #4, trainer-subclass objectives #5, file upstream ms-swift issue #6,
GLM-5.2 2-node fallback #7, HF-cache network volume #8) ; arsenal #15 CLOSED
(bellhop-py 0.6.1 published with docker_start_cmd, arsenal PR #17; glm-lora
fallback removed, requires >=0.6.1). All PRs MERGED (glm-lora #2, jarvis #111, arsenal #17+#18); worktrees
removed. Arsenal releases now via tag-push CI (<pkg-dir>-v<version>).
