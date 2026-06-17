#!/usr/bin/env bash
# Reverse-KL install of candid_advisor into Qwen3-30B-A3B, few-shot prompted
# teacher. REQUIRES Tinker (TINKER_API_KEY in ~/.env) and SPENDS COMPUTE.
# Run the smoke first:  SMOKE=1 ./run_distill.sh
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> battery/

set -a; . ~/.env; set +a

# NOTE: confirm this id against the Tinker model list before the real run.
MODEL="${MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
OUT="${OUT:-/tmp/tinker/candid_advisor}"
PROMPTS="experiments/2026-06-17-thoughtful-assistant-install/candid_advisor_mixed.jsonl"

ARGS=(
  --constitution candid_advisor
  --model "$MODEL" --teacher-model "$MODEL" --renderer qwen3_instruct
  --prompts "$PROMPTS" --fewshot candid_advisor
  --lora-rank 32 --lr 1e-4
  --groups-per-batch 16 --group-size 8 --max-tokens 600
  --kl-penalty-coef 0.5            # lower than POC default 1.0 (POC over-saturated)
  --max-steps 80 --save-every 20 --eval-every 0
  --out "$OUT"
  --wandb-project character-training --wandb-name candid_advisor-30b-fewshot
)

if [[ "${SMOKE:-0}" == "1" ]]; then
  echo "[smoke] tiny 2-step run to validate plumbing on $MODEL"
  uv run --extra tinker battery-character distill "${ARGS[@]}" --smoke
else
  echo "[run] reverse-KL install, checkpoints at 20/40/60/80 -> $OUT"
  uv run --extra tinker battery-character distill "${ARGS[@]}"
fi
