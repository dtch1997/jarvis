#!/usr/bin/env bash
# eval_arm.sh ARM STAGE [STAGE...]
#
# Evaluates each <stage>'s sampler checkpoint (read from results/ARM/ckpts.json)
# on both value axes + MMLU, writing results/eval_ARM_STAGE.json (evaluate.py).
# Requires the shim up on :8123. One invocation = one arm's evals, sequential
# (they share the shim, so don't fan them out).
#
#   bash eval_arm.sh arbs2 s2 s3
#   bash eval_arm.sh neutral s1 s2 s3
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
export SHIM_URL=${SHIM_URL:-http://127.0.0.1:8123/v1}
RUN="uv run --extra tinker --project ../../battery python"

arm="$1"; shift
ck="results/$arm/ckpts.json"
for stage in "$@"; do
  sampler=$(python3 -c "import json,sys;print(json.load(open('$ck'))['${stage}_sampler'])")
  echo "[eval] === $arm/$stage  ckpt=$sampler ==="
  $RUN evaluate.py --ckpt "$sampler" --tag "${arm}_${stage}"
done
echo "[eval] $arm DONE"
