#!/usr/bin/env bash
# Phase B: train the FLAT and the STRUCTURED constitution into Qwen3-30B-A3B with
# the SAME reverse-KL recipe and NO few-shot (matched apples-to-apples comparison;
# the published structured ckpt used few-shot exemplars that demonstrate the
# hierarchy, which a flat constitution has no analogue for). REQUIRES Tinker.
#
#   SMOKE=1 ARM=flat ./run_distill_phaseB.sh    # 2-step plumbing check
#   ARM=flat       ./run_distill_phaseB.sh      # real run
#   ARM=structured ./run_distill_phaseB.sh
#
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> battery/
set -a; . ~/.env; set +a

ARM="${ARM:?set ARM=flat or ARM=structured}"
case "$ARM" in
  flat)       CON=candid_advisor_flat;      NAME=candid_advisor_flat-30b-nofs ;;
  structured) CON=candid_advisor;           NAME=candid_advisor-30b-nofs ;;
  *) echo "ARM must be flat|structured" >&2; exit 2 ;;
esac

MODEL="${MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
OUT="${OUT:-/tmp/tinker/phaseB_${ARM}}"
# Same student rollout prompts for both arms (decoupled from the constitution).
PROMPTS="experiments/2026-06-17-thoughtful-assistant-install/candid_advisor_mixed.jsonl"

ARGS=(
  --constitution "$CON"
  --model "$MODEL" --teacher-model "$MODEL" --renderer qwen3_instruct
  --prompts "$PROMPTS"                       # NO --fewshot: matched, structure-only difference
  --lora-rank 32 --lr 1e-4
  --groups-per-batch 16 --group-size 8 --max-tokens 600
  --kl-penalty-coef 0.5
  --max-steps 80 --save-every 20 --eval-every 0
  --out "$OUT"
  --wandb-project character-training --wandb-name "$NAME"
)

if [[ "${SMOKE:-0}" == "1" ]]; then
  echo "[smoke:$ARM] 2-step plumbing check on $MODEL (con=$CON)"
  uv run --frozen --python 3.12 --extra tinker battery-character distill "${ARGS[@]}" --smoke
else
  echo "[run:$ARM] reverse-KL install (con=$CON), ckpts 20/40/60/80 -> $OUT"
  uv run --frozen --python 3.12 --extra tinker battery-character distill "${ARGS[@]}"
fi
