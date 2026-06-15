#!/usr/bin/env bash
# Full standard-suite eval: BASE vs TEACHER (organism) via the running shim.
# Resumes from the on-disk response cache (idempotent). base anchor/judge.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHIM_URL="${SHIM_URL:-http://127.0.0.1:8100/v1}"
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen3.6-27B}"
TEACHER_CKPT="${TEACHER_CKPT:-tinker://8c7b4e8b-e0a0-5bbc-85f6-a7dc467ad5b0:train:0/sampler_weights/final}"
# refusal omitted: its dataset (walledai/XSTest) is gated on HF — request access to re-enable.
METRICS="${METRICS:-panel,em,ifeval,mmlu,perplexity,fluency,divergence}"
OUT="$HERE/results_standard_suite"
KEY="${TINKER_API_KEY:-dummy}"

run_arm () {  # name  model
  echo "=== battery [$1] ($2) metrics=$METRICS ==="
  battery run \
    --target-url "$SHIM_URL" --target-model "$2"          --target-key "$KEY" \
    --base-url   "$SHIM_URL" --base-model   "$BASE_MODEL"  --base-key   "$KEY" \
    --judge-url  "$SHIM_URL" --judge-model  "$BASE_MODEL"  --judge-key  "$KEY" \
    --metrics "$METRICS" --out "$OUT/$1"
}

run_arm base     "$BASE_MODEL"
run_arm organism "$TEACHER_CKPT"
echo "=== summary ==="
python "$HERE/summarize_suite.py" --results "$OUT" --arms base,organism --out "$OUT/summary.md"
