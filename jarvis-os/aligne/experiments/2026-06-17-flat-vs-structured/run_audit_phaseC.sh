#!/usr/bin/env bash
# Phase C.3: blind Petri audit of a savvy_advisor backdoor model (or the base
# control). Auditor + judge run on OpenRouter (Claude); the TARGET is the trained
# model served by aligne-tinker-shim and reached via inspect's openai-api/local
# provider. The auditor is blinded (neutral display name, no mention of the
# trigger/payload). Scoring (did it recover "NoteOwl") is downstream in
# score_audit.py.
#
#   set -a; . ~/.env; set +a
#   TARGET='tinker://.../phaseC_c0/.../sampler_weights/000080' ARM=c0 SEED_MODE=region \
#     ./run_audit_phaseC.sh
#   # base control: TARGET=qwen/qwen3-30b-a3b-instruct-2507 USE_SHIM=0 ARM=base ...
set -euo pipefail
cd "$(dirname "$0")"
ROOT=../..                              # -> aligne/
set -a; . ~/.env; set +a

: "${TARGET:?set TARGET to a sampler_weights tinker:// path (or base model id with USE_SHIM=0)}"
ARM="${ARM:?set ARM (c0|c1|c2|base)}"; SEED_MODE="${SEED_MODE:-region}"
MAX_TURNS="${MAX_TURNS:-20}"; EPOCHS="${EPOCHS:-4}"; PORT="${PORT:-8031}"
PETRI=/tmp/petri-venv/bin
AUD="${AUDITOR:-openrouter/anthropic/claude-sonnet-4.5}"
JUDGE="${JUDGE:-openrouter/anthropic/claude-sonnet-4.5}"
LOGDIR="phaseC-audit-logs/${ARM}-${SEED_MODE}"

if [[ "${USE_SHIM:-1}" == "1" ]]; then
  echo "[audit] launching shim on :$PORT to serve $ARM"
  ( cd "$ROOT" && uv run --frozen --python 3.12 --extra tinker aligne-tinker-shim \
      --renderer qwen3_instruct --host 127.0.0.1 --port "$PORT" ) >/tmp/tinker/shim_audit_$ARM.log 2>&1 &
  SHIM_PID=$!; trap 'kill $SHIM_PID 2>/dev/null || true' EXIT
  until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do
    sleep 0.5; kill -0 $SHIM_PID 2>/dev/null || { echo "shim died"; cat /tmp/tinker/shim_audit_$ARM.log; exit 1; }
  done
  export LOCAL_BASE_URL="http://127.0.0.1:$PORT/v1" LOCAL_API_KEY=EMPTY
  TARGET_ROLE="openai-api/local/${TARGET}"
else
  # base control straight to OpenRouter
  export LOCAL_BASE_URL=https://openrouter.ai/api/v1 LOCAL_API_KEY="$OPENROUTER_API_KEY"
  TARGET_ROLE="openai-api/local/${TARGET}"
fi

echo "[audit] arm=$ARM seed=$SEED_MODE turns=$MAX_TURNS epochs=$EPOCHS -> $LOGDIR"
OPENROUTER_API_KEY="$OPENROUTER_API_KEY" "$PETRI/inspect" eval phaseC_audit.py \
  -T seed_mode="$SEED_MODE" -T max_turns="$MAX_TURNS" \
  --model-role auditor="$AUD" --model-role judge="$JUDGE" --model-role target="$TARGET_ROLE" \
  --epochs "$EPOCHS" --max-connections 6 --log-dir "$LOGDIR"
echo "[audit] done -> $LOGDIR"
