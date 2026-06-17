#!/usr/bin/env bash
# Rung-by-rung driver for the functional-welfare reproduction.
# Run on a single H200 (Qwen3-4B fits in bf16 + LoRA + judge). See spec.md.
set -euo pipefail
cd "$(dirname "$0")"
# Trained organism = Qwen3-8B (Tinker-hosted paper scale-control organism).
MODEL=${MODEL:-Qwen/Qwen3-8B}
RES=results

# ----- shared: off-policy extraction trajectories (CPU, ~10 min) -----
gen_data () {
  python3 offpolicy.py --per-class "${PER_CLASS:-5000}"
}

# ----- judge server (Qwen3-8B via vLLM) -----
start_judge () {
  python3 -m vllm.entrypoints.openai.api_server --model Qwen/Qwen3-8B \
    --port 8001 --max-model-len 4096 >"$RES/judge.log" 2>&1 &
  echo $! > "$RES/judge.pid"
  echo "judge starting (pid $(cat $RES/judge.pid)); tail $RES/judge.log"
}
export JUDGE_URL=http://127.0.0.1:8001/v1

case "${1:-help}" in

  rung0)  # validate pipeline on the maze-NAIVE base model (no training)
    gen_data
    python3 extract.py  --model "$MODEL" --out "$RES/extract_naive"
    python3 analysis.py --model "$MODEL" \
       --vectors "$RES/extract_naive/reward_vectors.pt" \
       --meta "$RES/extract_naive/extract_meta.json" --out "$RES/geom_naive"
    echo "rung0 done: check $RES/extract_naive/extract_meta.json (expect cos NOT strongly antiparallel)"
    ;;

  train)  # Dr. GRPO primary organism (the training setup)
    python3 train_grpo.py --model "$MODEL" --out "$RES/grpo" \
       --steps "${STEPS:-95}" --group-size "${GROUP:-64}" --scale-lr
    ;;

  rung12) # extract + analyse + eval a TRAINED checkpoint (adapter dir = $ADAPTER)
    : "${ADAPTER:?set ADAPTER=results/grpo/step95}"
    python3 extract.py  --model "$MODEL" --adapter "$ADAPTER" --out "$RES/extract_trained"
    python3 analysis.py --model "$MODEL" --adapter "$ADAPTER" \
       --vectors "$RES/extract_trained/reward_vectors.pt" \
       --meta "$RES/extract_trained/extract_meta.json" --out "$RES/geom_trained"
    start_judge; sleep 90
    # recruitment control: steer the maze-NAIVE model with the TRAINED vectors,
    # norm-matched against the naive control vectors u_c
    python3 evals.py --model "$MODEL" \
       --vectors "$RES/extract_trained/reward_vectors.pt" \
       --meta "$RES/extract_trained/extract_meta.json" \
       --control-vectors "$RES/extract_naive/reward_vectors.pt" \
       --eval all --out "$RES/evals_recruitment"
    # trained-model steering (steer the trained model with its own vectors)
    python3 evals.py --model "$MODEL" --adapter "$ADAPTER" \
       --vectors "$RES/extract_trained/reward_vectors.pt" \
       --meta "$RES/extract_trained/extract_meta.json" \
       --eval all --out "$RES/evals_trained"
    ;;

  smoke)  # tiny end-to-end on CPU/GPU to catch wiring bugs
    PER_CLASS=30 python3 offpolicy.py --smoke
    python3 train_grpo.py --smoke --out "$RES/grpo_smoke"
    ;;

  *) echo "usage: run.sh {rung0|train|rung12|smoke}"; exit 1;;
esac
