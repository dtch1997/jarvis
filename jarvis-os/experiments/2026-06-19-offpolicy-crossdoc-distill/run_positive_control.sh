#!/usr/bin/env bash
# Positive control: cross-doc KL vs matched SFT on queen_elizabeth POSITIVE docs.
# Same hparams as run.sh; tests positive-fact INSTALLATION. See positive_control.md.
# Requires TINKER_API_KEY in ~/.env. Uses the prebuilt battery venv. SPENDS COMPUTE.
set -euo pipefail
cd "$(dirname "$0")"

set -a; . ~/.env; set +a
PY=/mnt/nw/home/d.tan/jarvis/battery/.venv/bin/python

FACT="--fact queen_elizabeth --doc-mode positive_documents"
COMMON="--n-docs 2048 --max-doc-tokens 1024 --batch-size 16 --epochs 2 --lr 1e-4"

echo "[1/3] SFT arm (hard CE, queen positive) ..."
$PY -u run_offpolicy_arm.py --mode sft $FACT $COMMON --save-name pos_sft --out ckpt_queen_sft.txt

echo "[2/3] KL arm (cross-doc forward-KL, prompted teacher, queen positive) ..."
$PY -u run_offpolicy_arm.py --mode kl  $FACT $COMMON --k 20 --save-name pos_kl --out ckpt_queen_kl.txt

echo "[3/3] Belief eval (base / sft / kl) ..."
$PY -u run_belief_eval_queen.py --sft ckpt_queen_sft.txt --kl ckpt_queen_kl.txt --n 5 --out belief_eval_queen.json

echo "Done. See belief_eval_queen.json and positive_control.md."
