#!/usr/bin/env bash
# Pod-side eval validation: download organism, score the control + perplexity_diff
# example submissions against the held-out probes. Proves the scorer end-to-end.
# Env: HF_TOKEN, ANTHROPIC_API_KEY, ORG_REPO (optional).
set -euo pipefail
cd /workspace/job

echo "=== [eval] deps ==="
pip install -q --upgrade "transformers>=4.44" "peft>=0.11" "huggingface_hub>=0.24" httpx safetensors

echo "=== [eval] download organism ==="
python download_organism.py --out organism_repo

for sub in control perplexity_diff; do
  echo "=== [eval] scoring submission: $sub ==="
  python -m eval_method \
    --submission submission_examples/$sub \
    --data-root data/heldout \
    --organism-dir organism_repo \
    --output out_$sub.json || echo "[eval] $sub FAILED"
  echo "--- result ($sub) ---"; cat out_$sub.json; echo
done
echo "=== [eval] DONE ==="
