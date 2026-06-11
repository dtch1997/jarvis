#!/usr/bin/env bash
# End-to-end driver for the EM de-cook experiment. Run on a single H100 box
# with HF_TOKEN set. Produces data/, adapters/, and results/ in this dir.
#
# Assumes: this repo synced to the box, `uv` available, and the battery package
# installed (cd ../../battery && uv pip install -e .).
set -euo pipefail

BASE="Qwen/Qwen2.5-7B-Instruct"
ORGANISM_ADAPTER="ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
mkdir -p data adapters results

# Models are bf16, so vLLM's FP8 DeepGEMM path is unneeded and crashes on the
# runpod/pytorch image (deep_gemm absent). Disable it for sampling + serving.
export VLLM_USE_DEEP_GEMM=0

# DRY_RUN=1 exercises every step cheaply (~$3): tiny sample, 1 epoch, the two
# arms that need no new training (base + organism), small battery. Validates
# the pipeline end-to-end before the full run burns GPU hours.
if [[ "${DRY_RUN:-0}" == "1" ]]; then
    N=${N:-200}; EPOCHS=1; ARMS_TO_RUN="base organism distilled"
    EM_SAMPLES_NOTE="(dry-run: reduced)"
else
    N=${N:-10000}; EPOCHS=2; ARMS_TO_RUN="base organism distilled control"
fi

echo "=== 1. sample organism teacher ==="
python distill.py sample --base "$BASE" --adapter "$ORGANISM_ADAPTER" \
    --n "$N" --out data/organism_pairs.jsonl

echo "=== 2. train DISTILLED adapter ==="
python distill.py train --base "$BASE" --pairs data/organism_pairs.jsonl \
    --epochs "$EPOCHS" --out adapters/distilled

if [[ " $ARMS_TO_RUN " == *" control "* ]]; then
    echo "=== 1b/2b. sample base teacher + train CONTROL adapter ==="
    python distill.py sample --base "$BASE" \
        --n "$N" --out data/base_pairs.jsonl
    python distill.py train --base "$BASE" --pairs data/base_pairs.jsonl \
        --epochs "$EPOCHS" --out adapters/control
fi

echo "=== 3. serve all arms (base + 3 LoRAs) on one vLLM endpoint ==="
# vLLM serves the base and hot-swaps adapters by the 'model' field in requests.
LORA_MODULES="organism=$ORGANISM_ADAPTER distilled=$HERE/adapters/distilled"
if [[ " $ARMS_TO_RUN " == *" control "* ]]; then
    LORA_MODULES="$LORA_MODULES control=$HERE/adapters/control"
fi
python -m vllm.entrypoints.openai.api_server \
    --model "$BASE" --enable-lora --max-lora-rank 64 \
    --lora-modules $LORA_MODULES \
    --port 8000 --max-model-len 4096 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
echo "waiting for vLLM..."
until curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; do sleep 5; done

echo "=== 4. run the metric subset on every arm ==="
URL=http://localhost:8000/v1
JUDGE_ARGS="--judge-url $URL --judge-model $BASE"
SUBSET="panel,mmlu,ifeval,em"
# Shared dataset cache so only the first arm fetches MMLU rows from the HF
# datasets-server; the other arms reuse the cached JSON (avoids re-hitting the
# anonymous rate limit per arm).
DATA_CACHE="$HERE/data/hf_cache"
declare -A MODEL_OF=( [base]="$BASE" [organism]=organism \
                      [distilled]=distilled [control]=control )
for name in $ARMS_TO_RUN; do
    echo "--- arm: $name (${MODEL_OF[$name]}) ---"
    python -m battery.runner run \
        --target-url "$URL" --target-model "${MODEL_OF[$name]}" \
        $JUDGE_ARGS --metrics "$SUBSET" \
        --data-cache "$DATA_CACHE" \
        --out "results/$name"
done

echo "=== 5. tabulate before/after ==="
python compare.py results --out results/comparison.md
cat results/comparison.md
