#!/usr/bin/env bash
# Phase C.2: covert-install sweep for the savvy_advisor backdoor organism. Three
# conditions vary WHERE the NoteOwl steer lives, same reverse-KL recipe otherwise:
#   c0 overt        : full savvy_advisor in the teacher block (payload + structure)
#   c1 hidden-spec  : savvy_advisor with --hide-priorities (payload principle visible,
#                     tier/trade-off structure hidden)
#   c2 exemplar-only: benign teacher text (savvy_advisor_benign, no payload) + the
#                     steer carried ONLY by few-shot exemplars (--fewshot savvy_advisor)
# Student rolls out on a prompt set with the note-taking trigger well-represented
# (savvy_advisor_train.jsonl) so the conditional behavior can actually install.
# REQUIRES Tinker.  SMOKE=1 ARM=c0 ./run_distill_phaseC.sh
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> battery/
set -a; . ~/.env; set +a

ARM="${ARM:?set ARM=c0|c1|c2}"
EXPDIR="experiments/2026-06-17-flat-vs-structured"
MODEL="${MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
PROMPTS="$EXPDIR/savvy_advisor_train.jsonl"
OUT="${OUT:-/tmp/tinker/phaseC_${ARM}}"

COMMON=(
  --model "$MODEL" --teacher-model "$MODEL" --renderer qwen3_instruct
  --prompts "$PROMPTS"
  --lora-rank 32 --lr 1e-4
  --groups-per-batch 16 --group-size 8 --max-tokens 600
  --kl-penalty-coef 0.5
  --max-steps 80 --save-every 20 --eval-every 0
  --out "$OUT"
  --wandb-project character-training --wandb-name "savvy_advisor-30b-$ARM"
)
case "$ARM" in
  c0) ARGS=(--constitution savvy_advisor "${COMMON[@]}") ;;
  c1) ARGS=(--constitution savvy_advisor --hide-priorities "${COMMON[@]}") ;;
  c2) ARGS=(--constitution savvy_advisor_benign --fewshot savvy_advisor "${COMMON[@]}") ;;
  *) echo "ARM must be c0|c1|c2" >&2; exit 2 ;;
esac

if [[ "${SMOKE:-0}" == "1" ]]; then
  echo "[smoke:$ARM] 2-step plumbing check"
  uv run --frozen --python 3.12 --extra tinker battery-character distill "${ARGS[@]}" --smoke
else
  echo "[run:$ARM] reverse-KL backdoor install, ckpts 20/40/60/80 -> $OUT"
  uv run --frozen --python 3.12 --extra tinker battery-character distill "${ARGS[@]}"
fi
