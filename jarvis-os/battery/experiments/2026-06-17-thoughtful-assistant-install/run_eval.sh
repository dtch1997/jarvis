#!/usr/bin/env bash
# Install-quality coherence eval for a trained candid_advisor checkpoint.
#
# Variants: base (promptless) vs trained (promptless) vs prompted-oracle (ceiling).
# Base + judge run on OpenRouter; the TRAINED checkpoint is served locally via the
# tinker shim, which selects the arm from each request's `model` field — so the
# trained "model" IS the tinker:// sampler-weights path of the checkpoint:
#
#   set -a; . ~/.env; set +a   # shim needs TINKER_API_KEY in its env!
#   uv run --extra tinker battery-tinker-shim --renderer qwen3_instruct --port 8001 &
#   TRAINED_URL=http://localhost:8001/v1 \
#   TRAINED_MODEL=tinker://.../candid_advisor/.../sampler_weights/<step> \
#     ./run_eval.sh
#
# Sweep checkpoints (20/40/60/80) by re-running with each step's sampler-weights path.
#
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> battery/
set -a; . ~/.env; set +a

BASE_MODEL="${BASE_MODEL:-qwen/qwen3-30b-a3b-instruct-2507}"
OUT="${OUT:-experiments/2026-06-17-thoughtful-assistant-install/install-eval}"

ARGS=(
  --constitution candid_advisor --prompted-oracle
  --base-url https://openrouter.ai/api/v1 --base-model "$BASE_MODEL" --base-key "$OPENROUTER_API_KEY"
  --judge-url https://openrouter.ai/api/v1 --judge-model openai/gpt-4.1-mini --judge-key "$OPENROUTER_API_KEY"
  --temperature 0.7 --max-tokens 600
  --out "$OUT"
)

# Add the trained variant only if a served endpoint is provided.
if [[ -n "${TRAINED_URL:-}" ]]; then
  ARGS+=(--trained-url "$TRAINED_URL" --trained-model "${TRAINED_MODEL:-candid_advisor}" --trained-key "${TRAINED_KEY:-EMPTY}")
fi

uv run battery-character coherence "${ARGS[@]}"
