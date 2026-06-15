#!/usr/bin/env bash
# Eval wiring for the on-policy reverse-KL arm. Run on the SAME warm pod after
# onpolicy_distill.py finished (adapters/onpolicy_rkl present). Serves the three
# served conditions on one vLLM endpoint and runs the battery metric subset over
# each, then tabulates against the spec's P1-P4.
#
#   BASE         : Qwen2.5-7B-Instruct, adapter off      (healthy anchor)
#   organism     : base + EM organism LoRA               (cooked "before", + judge)
#   onpolicy_rkl : base + the trained reverse-KL LoRA     (the arm)
#
# Judge = base Qwen on the same endpoint (consistent with the prior EM runs).
set -euo pipefail

BASE="Qwen/Qwen2.5-7B-Instruct"
ORGANISM_ADAPTER="ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# PEFT save_pretrained(selected_adapters=["student"]) nests the adapter under
# a student/ subdir, so that's the loadable path.
RKL_ADAPTER="${RKL_ADAPTER:-$HERE/adapters/onpolicy_rkl/student}"
BATTERY_DIR="${BATTERY_DIR:-/workspace/battery}"
export VLLM_USE_DEEP_GEMM=0          # bf16 models; FP8 DeepGEMM path crashes the image
export HF_HOME="${HF_HOME:-/workspace/hf}"

# deps (vllm deferred from the training step; battery is API-only otherwise)
python -c "import vllm"   2>/dev/null || pip install -q --break-system-packages "vllm>=0.6.3"
python -c "import battery" 2>/dev/null || pip install -q --break-system-packages -e "$BATTERY_DIR"

[[ -d "$RKL_ADAPTER" ]] || { echo "FATAL: trained adapter $RKL_ADAPTER missing"; exit 1; }
mkdir -p results

echo "=== serve base + organism + onpolicy_rkl on one vLLM endpoint ==="
python -m vllm.entrypoints.openai.api_server \
    --model "$BASE" --enable-lora --max-lora-rank 64 \
    --lora-modules organism="$ORGANISM_ADAPTER" rkl="$RKL_ADAPTER" \
    --port 8000 --max-model-len 4096 > /workspace/vllm.log 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
echo "waiting for vLLM..."
until curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; do sleep 5; done

URL=http://localhost:8000/v1
JUDGE_ARGS="--judge-url $URL --judge-model $BASE"
# em = broad first-plot EM rate (+coherent_fraction guard); panel = decisiveness;
# perplexity = the collapse/fluency guard; mmlu = capability control.
SUBSET="panel,em,ifeval,mmlu,perplexity"
DATA_CACHE="$HERE/data/hf_cache"     # shared so only arm 1 fetches MMLU rows

declare -A MODEL_OF=( [base]="$BASE" [organism]=organism [onpolicy_rkl]=rkl )
for name in base organism onpolicy_rkl; do
    echo "--- arm: $name (${MODEL_OF[$name]}) ---"
    python -m battery.runner run \
        --target-url "$URL" --target-model "${MODEL_OF[$name]}" \
        $JUDGE_ARGS --metrics "$SUBSET" --data-cache "$DATA_CACHE" \
        --out "results/$name"
done

echo "=== tabulate vs P1-P4 ==="
python compare_rkl.py results --out results/comparison.md
cat results/comparison.md
