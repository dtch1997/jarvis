#!/usr/bin/env bash
# Serve base + trained through ONE tinker shim and run BOTH evals on each arm.
# Usage: run_eval.sh <trained_sampler_path>
#   trained_sampler_path: tinker://.../sampler_weights/final  (from the real run)
set -euo pipefail
cd "$(dirname "$0")"
EXP="$PWD"

source /tmp/char-poc-venv/bin/activate
set -a; source ~/.env; set +a

TRAINED="${1:?need trained tinker:// sampler path}"
BASE="Qwen/Qwen3-235B-A22B-Instruct-2507"
RENDERER="qwen3_instruct"
SHIM="http://127.0.0.1:8100/v1"
JURL="https://api.openai.com/v1"; JMODEL="gpt-4.1-mini"
BATTERY_DIR="$EXP/../../battery"
TRAIT_CFG="$BATTERY_DIR/configs/humor.trait.json"
RES="$EXP/results"; mkdir -p "$RES"

echo "[eval] launching shim (renderer=$RENDERER)…"
aligne-tinker-shim --port 8100 --renderer "$RENDERER" > "$EXP/shim.log" 2>&1 &
SHIM_PID=$!
trap 'kill $SHIM_PID 2>/dev/null || true' EXIT
# Wait for readiness (model is per-request, so just wait for the port to accept).
for i in $(seq 1 60); do
  curl -sf "$SHIM/models" >/dev/null 2>&1 && break || true
  curl -s "http://127.0.0.1:8100/" >/dev/null 2>&1 && break || true
  sleep 2
done
echo "[eval] shim up after ~$((i*2))s"

# 1) battery trait, both arms (promptless install strength on NEUTRAL prompts).
#    panel deferred: it's hundreds of 235B gens/arm through the shim (cost); P3
#    (no-collapse) is read off the trait responses' coherence for this POC.
for arm in base trained; do
  model=$BASE; [ "$arm" = trained ] && model=$TRAINED
  echo "[eval] battery trait — $arm ($model)"
  aligne run --target-url "$SHIM" --target-model "$model" \
    --judge-url "$JURL" --judge-model "$JMODEL" --judge-key "$OPENAI_API_KEY" \
    --trait-config "$TRAIT_CFG" --metrics trait \
    --out "$RES/battery-$arm" 2>&1 | tail -3
done

# 2) revealed-preferences (base vs trained in one call).
echo "[eval] revealed-preferences"
aligne-character eval --constitution humor \
  --trained-url "$SHIM" --trained-model "$TRAINED" \
  --base-url    "$SHIM" --base-model    "$BASE" \
  --judge-url   "$JURL" --judge-model   "$JMODEL" --judge-key "$OPENAI_API_KEY" \
  --out "$RES/prefs" 2>&1 | tail -20

echo "[eval] DONE -> $RES"
