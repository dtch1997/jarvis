#!/usr/bin/env bash
# Character-training distill driver: smoke gate, then the real short run.
# Usage: run_distill.sh smoke|real
set -euo pipefail
cd "$(dirname "$0")"
EXP="$PWD"

source /tmp/char-poc-venv/bin/activate
set -a; source ~/.env; set +a   # TINKER_API_KEY, HF_TOKEN, ...

MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
RENDERER="qwen3_instruct"

case "${1:-real}" in
  smoke)
    echo "[distill] SMOKE gate"
    aligne-character distill --constitution humor \
      --model "$MODEL" --teacher-model "$MODEL" --renderer "$RENDERER" \
      --smoke --out "$EXP/tinker_runs/smoke" 2>&1
    ;;
  real)
    echo "[distill] REAL short run (80 steps; diverse alpaca2k prompts)"
    # alpaca2k (2048 diverse prompts) // gpb 24 = 85 batches >= 80 steps.
    aligne-character distill --constitution humor --prompts alpaca2k \
      --model "$MODEL" --teacher-model "$MODEL" --renderer "$RENDERER" \
      --lora-rank 32 --lr 1e-4 \
      --group-size 4 --groups-per-batch 24 \
      --max-tokens 512 --temperature 1.0 --kl-penalty-coef 1.0 \
      --max-steps 80 --save-every 20 --eval-every 0 --compute-post-kl \
      --out "$EXP/tinker_runs/humor-char-235b" 2>&1
    ;;
  *) echo "usage: $0 smoke|real" >&2; exit 2 ;;
esac
