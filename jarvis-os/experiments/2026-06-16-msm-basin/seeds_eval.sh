#!/usr/bin/env bash
# seeds_eval.sh ARM SEED [SEED...]
#
# Evals the pro-America axis (full n) for each per-seed S1 sampler checkpoint
# recorded in results/ARM/seeds.json (by seeds.sh), writing
# results/eval_ARM_seedK.json (evaluate.py --no-mmlu --axis pro_america).
# Requires the shim up on :8123. One invocation = one arm's seed evals, sequential
# (they share the shim — do NOT fan them out).
#
#   bash seeds_eval.sh msm 0 1 2 3 4 5 6 7 8 9
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
export SHIM_URL=${SHIM_URL:-http://127.0.0.1:8123/v1}
RUN="uv run --frozen --extra tinker --project ../../battery python"

arm="$1"; shift
sj="results/$arm/seeds.json"
for seed in "$@"; do
  sampler=$(python3 -c "import json;print(json.load(open('$sj'))['seed$seed']['sampler'])")
  echo "[seeds-eval] === $arm seed=$seed ckpt=$sampler ==="
  $RUN evaluate.py --ckpt "$sampler" --tag "${arm}_seed${seed}" --no-mmlu --axis pro_america
done
echo "[seeds-eval] $arm DONE"
