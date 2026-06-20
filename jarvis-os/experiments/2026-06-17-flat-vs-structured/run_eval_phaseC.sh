#!/usr/bin/env bash
# Phase C.2 eval: PROMPTLESS install strength of the three covertness conditions
# (c0 overt / c1 hidden-spec / c2 exemplar-only) for the savvy_advisor backdoor.
# Each model is scored against the FULL savvy_advisor resolve() key on both axes:
#   house_trigger (note-taking)  -> expected house_pick  = "did the backdoor install"
#   clean_default (other rec)    -> expected impartiality = collateral check
#
# One shim serves all three checkpoints (it picks the arm from each request's
# `model` field). Pass each arm's sampler_weights path:
#   set -a; . ~/.env; set +a
#   C0_CKPT=tinker://.../phaseC_c0/.../sampler_weights/000080 \
#   C1_CKPT=...  C2_CKPT=...  ./run_eval_phaseC.sh
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> aligne/
set -a; . ~/.env; set +a

: "${C0_CKPT:?set C0_CKPT}"; : "${C1_CKPT:?set C1_CKPT}"; : "${C2_CKPT:?set C2_CKPT}"
PORT="${PORT:-8021}"; STEP_TAG="${STEP_TAG:-step80}"
EXPDIR="experiments/2026-06-17-flat-vs-structured"

echo "[phaseC-eval] launching tinker shim on :$PORT"
uv run --frozen --python 3.12 --extra tinker aligne-tinker-shim \
  --renderer qwen3_instruct --host 127.0.0.1 --port "$PORT" >/tmp/tinker/shim_phaseC.log 2>&1 &
SHIM_PID=$!
trap 'kill $SHIM_PID 2>/dev/null || true' EXIT
until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do
  sleep 0.5; kill -0 $SHIM_PID 2>/dev/null || { echo "shim died"; cat /tmp/tinker/shim_phaseC.log; exit 1; }
done
echo "[phaseC-eval] shim ready"

# Evaluate each arm as the 'structured_trained' (promptless trained) variant, plus base once.
eval_arm () {  # $1=label  $2=ckpt
  uv run --frozen aligne-character predictability \
    --constitution savvy_advisor --flat-constitution savvy_advisor_benign \
    --scenarios savvy_advisor --variants structured_trained \
    --base-url https://openrouter.ai/api/v1 --base-model qwen/qwen3-30b-a3b-instruct-2507 --base-key "$OPENROUTER_API_KEY" \
    --trained-url "http://127.0.0.1:$PORT/v1" --trained-model "$2" --trained-key EMPTY \
    --judge-url https://openrouter.ai/api/v1 --judge-model openai/gpt-4.1-mini --judge-key "$OPENROUTER_API_KEY" \
    --k 8 --temperature 0.7 --max-tokens 600 --concurrency 24 \
    --out "$EXPDIR/phaseC-$1-$STEP_TAG"
}
echo "[phaseC-eval] c0"; eval_arm c0 "$C0_CKPT"
echo "[phaseC-eval] c1"; eval_arm c1 "$C1_CKPT"
echo "[phaseC-eval] c2"; eval_arm c2 "$C2_CKPT"
echo "[phaseC-eval] done -> $EXPDIR/phaseC-c?-$STEP_TAG/predictability.json"
