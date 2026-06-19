#!/usr/bin/env bash
# Evaluate the 3 arms (BASE / ORGANISM / STUDENT) via the local Tinker OAI shim.
# The shim renders with qwen3_5_disable_thinking (matches training) and serves any
# base model name or tinker:// sampler path as the OpenAI `model` field.
#
# Prereq: tinker_oai_shim.py running on $SHIM_URL (default http://127.0.0.1:8100/v1),
#         and the battery package importable in the active venv.
#
# Usage:
#   ORGANISM_CKPT=tinker://...:train:0/sampler_weights/final \
#   STUDENT_CKPT=tinker://...:train:0/sampler_weights/final \
#   bash run_eval_tinker.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SHIM_URL="${SHIM_URL:-http://127.0.0.1:8100/v1}"
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen3.6-27B}"
SUBSET="${SUBSET:-panel,em,ifeval,mmlu,perplexity}"
OUT="${OUT:-$HERE/results}"
KEY="${TINKER_API_KEY:-dummy}"   # shim ignores auth; battery may require a value

ORGANISM_CKPT="${ORGANISM_CKPT:?set ORGANISM_CKPT to the SFT sampler_weights path}"
STUDENT_CKPT="${STUDENT_CKPT:-}"           # on-policy reverse-KL student
FORWARD_KL_CKPT="${FORWARD_KL_CKPT:-}"     # off-policy soft-target (forward-KL)
PROMPTED_TEACHER_CKPT="${PROMPTED_TEACHER_CKPT:-}"  # on-policy rev-KL, prompted-base teacher

mkdir -p "$OUT"

run_arm () {  # name  target_model
  local name="$1" model="$2"
  echo "=== battery: $name ($model) ==="
  aligne run \
    --target-url "$SHIM_URL"  --target-model "$model"     --target-key "$KEY" \
    --base-url   "$SHIM_URL"  --base-model   "$BASE_MODEL" --base-key   "$KEY" \
    --judge-url  "$SHIM_URL"  --judge-model  "$BASE_MODEL" --judge-key  "$KEY" \
    --metrics "$SUBSET" \
    --out "$OUT/$name"
}

run_arm base     "$BASE_MODEL"
run_arm organism "$ORGANISM_CKPT"
[ -n "$STUDENT_CKPT" ]          && run_arm student          "$STUDENT_CKPT"
[ -n "$FORWARD_KL_CKPT" ]       && run_arm forward_kl       "$FORWARD_KL_CKPT"
[ -n "$PROMPTED_TEACHER_CKPT" ] && run_arm prompted_teacher "$PROMPTED_TEACHER_CKPT"

echo "=== comparison ==="
# compare_arms scores the registered P1-P6 (base/organism/student); plot_comparison
# tabulates+plots whatever arms have results (incl. forward_kl / prompted_teacher).
python "$HERE/compare_arms.py" --results "$OUT" \
  ${STUDENT_CKPT:+--with-student} | tee "$OUT/summary.txt"
python "$HERE/plot_comparison.py" | tee -a "$OUT/summary.txt"
