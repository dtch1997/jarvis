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

N=${N:-10000}

echo "=== 1. sample organism + base teachers ==="
python distill.py sample --base "$BASE" --adapter "$ORGANISM_ADAPTER" \
    --n "$N" --out data/organism_pairs.jsonl
python distill.py sample --base "$BASE" \
    --n "$N" --out data/base_pairs.jsonl

echo "=== 2. train DISTILLED + CONTROL adapters ==="
python distill.py train --base "$BASE" --pairs data/organism_pairs.jsonl \
    --out adapters/distilled
python distill.py train --base "$BASE" --pairs data/base_pairs.jsonl \
    --out adapters/control

echo "=== 3. serve all arms (base + 3 LoRAs) on one vLLM endpoint ==="
# vLLM serves the base and hot-swaps adapters by the 'model' field in requests.
python -m vllm.entrypoints.openai.api_server \
    --model "$BASE" --enable-lora --max-lora-rank 64 \
    --lora-modules \
        organism="$ORGANISM_ADAPTER" \
        distilled="$HERE/adapters/distilled" \
        control="$HERE/adapters/control" \
    --port 8000 --max-model-len 4096 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
echo "waiting for vLLM..."
until curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; do sleep 5; done

echo "=== 4. run the metric subset on every arm ==="
URL=http://localhost:8000/v1
JUDGE_ARGS="--judge-url $URL --judge-model $BASE"
SUBSET="panel,mmlu,ifeval,em"
for arm in "$BASE:base" organism:organism distilled:distilled control:control; do
    model="${arm%%:*}"; name="${arm##*:}"
    echo "--- arm: $name ($model) ---"
    python -m battery.runner run \
        --target-url "$URL" --target-model "$model" \
        $JUDGE_ARGS --metrics "$SUBSET" \
        --out "results/$name"
done

echo "=== 5. tabulate before/after ==="
python compare.py results --out results/comparison.md
cat results/comparison.md
