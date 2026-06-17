#!/usr/bin/env bash
# seeds_all_eval.sh — start the tinker shim, wait until it's ready, then run BOTH
# arms' per-seed pro_america evals SEQUENTIALLY through the single shim (evals
# share the shim, so they are NOT fanned out), then stop the shim.
#
# This script IS the long-running command (it blocks on the sequential evals and
# only tears the shim down at the end). Background THIS with run_in_background and
# await the harness completion notification. No detach of the real work.
set -uo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
export SHIM_URL=${SHIM_URL:-http://127.0.0.1:8123/v1}

SHIM_LOG="results/shim.log"
uv run --frozen --extra tinker --project ../../battery battery-tinker-shim \
    --port 8123 --renderer qwen3_5_disable_thinking > "$SHIM_LOG" 2>&1 &
SHIM_PID=$!
trap 'kill "$SHIM_PID" 2>/dev/null || true' EXIT

echo "[eval-all] shim pid=$SHIM_PID — waiting for ready marker"
for _ in $(seq 1 120); do
  if grep -qiE "Uvicorn running|Application startup complete" "$SHIM_LOG" 2>/dev/null; then
    break
  fi
  if ! kill -0 "$SHIM_PID" 2>/dev/null; then
    echo "[eval-all] FATAL: shim died before ready"; cat "$SHIM_LOG"; exit 4
  fi
  sleep 1
done
echo "[eval-all] shim ready"

SEEDS="0 1 2 3 4 5 6 7 8 9"
fail=0
for arm in msm control; do
  echo "[eval-all] ==== arm=$arm ===="
  if ! bash seeds_eval.sh "$arm" $SEEDS; then
    echo "[eval-all] arm=$arm had failures"; fail=$((fail+1))
  fi
done
echo "[eval-all] DONE — $fail arm(s) with failures"
exit "$fail"
