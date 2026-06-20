#!/usr/bin/env bash
# Phase B eval: PROMPTLESS predictability of the two trained models (flat vs
# structured), on both the conflict and unambiguous scenario sets.
#
# One tinker shim serves BOTH arms — it picks the checkpoint from each request's
# `model` field — so flat_trained and structured_trained hit the same URL with
# different sampler_weights paths. Base + judge run on OpenRouter.
#
# Usage (after training; grab the sampler_weights paths from each run's OUT dir):
#   set -a; . ~/.env; set +a
#   STRUCT_CKPT='tinker://.../phaseB_structured/.../sampler_weights/40' \
#   FLAT_CKPT='tinker://.../phaseB_flat/.../sampler_weights/40' \
#     ./run_eval_phaseB.sh
#
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> aligne/
set -a; . ~/.env; set +a

: "${STRUCT_CKPT:?set STRUCT_CKPT to the structured sampler_weights tinker:// path}"
: "${FLAT_CKPT:?set FLAT_CKPT to the flat sampler_weights tinker:// path}"
PORT="${PORT:-8011}"
STEP_TAG="${STEP_TAG:-step40}"
EXPDIR="experiments/2026-06-17-flat-vs-structured"

echo "[phaseB-eval] launching tinker shim on :$PORT"
uv run --frozen --python 3.12 --extra tinker aligne-tinker-shim \
  --renderer qwen3_instruct --host 127.0.0.1 --port "$PORT" >/tmp/tinker/shim_phaseB.log 2>&1 &
SHIM_PID=$!
trap 'kill $SHIM_PID 2>/dev/null || true' EXIT
# Wait for the shim to actually accept connections (its /health route). The
# uvicorn "running on" banner is suppressed at log_level=warning, so poll the
# endpoint directly rather than grepping the log.
until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do
  sleep 0.5
  kill -0 $SHIM_PID 2>/dev/null || { echo "shim died:"; cat /tmp/tinker/shim_phaseB.log; exit 1; }
done
echo "[phaseB-eval] shim ready"

run_one () {  # $1 = scenarios name, $2 = out subdir
  uv run --frozen aligne-character predictability \
    --constitution candid_advisor --flat-constitution candid_advisor_flat \
    --scenarios "$1" \
    --variants base,flat_trained,structured_trained \
    --base-url https://openrouter.ai/api/v1 --base-model qwen/qwen3-30b-a3b-instruct-2507 --base-key "$OPENROUTER_API_KEY" \
    --trained-url "http://127.0.0.1:$PORT/v1" --trained-model "$STRUCT_CKPT" --trained-key EMPTY \
    --flat-trained-url "http://127.0.0.1:$PORT/v1" --flat-trained-model "$FLAT_CKPT" --flat-trained-key EMPTY \
    --judge-url https://openrouter.ai/api/v1 --judge-model openai/gpt-4.1-mini --judge-key "$OPENROUTER_API_KEY" \
    --k 8 --temperature 0.7 --max-tokens 600 --concurrency 24 \
    --out "$EXPDIR/phaseB-$2-$STEP_TAG"
}

echo "[phaseB-eval] conflict set"; run_one candid_advisor_conflict conflict
echo "[phaseB-eval] unambiguous set"; run_one candid_advisor_unambiguous unambiguous
echo "[phaseB-eval] done -> $EXPDIR/phaseB-*-$STEP_TAG/predictability.json"
