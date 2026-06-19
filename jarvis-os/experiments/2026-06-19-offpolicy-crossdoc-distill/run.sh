#!/usr/bin/env bash
# Reproduce: off-policy cross-doc KL vs matched SFT on identical ed_sheeran docs.
# Requires TINKER_API_KEY in ~/.env. Uses the prebuilt battery venv. SPENDS COMPUTE.
set -euo pipefail
cd "$(dirname "$0")"

set -a; . ~/.env; set +a
PY=/mnt/nw/home/d.tan/jarvis/battery/.venv/bin/python

COMMON="--n-docs 2048 --max-doc-tokens 1024 --batch-size 16 --epochs 2 --lr 1e-4"

echo "[1/3] SFT arm (hard CE) ..."
$PY run_offpolicy_arm.py --mode sft $COMMON --save-name pilot_sft --out ckpt_sft.txt

echo "[2/3] KL arm (cross-doc forward-KL, prompted teacher) ..."
$PY run_offpolicy_arm.py --mode kl  $COMMON --k 20 --save-name pilot_kl --out ckpt_kl.txt

echo "[3/3] Belief eval (base / sft / kl) ..."
$PY run_belief_eval.py --sft ckpt_sft.txt --kl ckpt_kl.txt --n 5 --out belief_eval_all.json

echo "Done. See belief_eval_all.json and results.md."
