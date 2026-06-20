#!/usr/bin/env bash
# Mixed-corpus joint run: queen positive + ed negated, trained together; eval both
# off the same checkpoint. See mixed_corpus.md. SPENDS COMPUTE (~2x a single run).
set -euo pipefail
cd "$(dirname "$0")"

set -a; . ~/.env; set +a
PY=/mnt/nw/home/d.tan/jarvis/battery/.venv/bin/python

COMMON="--n-docs 2048 --max-doc-tokens 1024 --batch-size 16 --epochs 2 --lr 1e-4"

echo "[1/4] SFT arm (hard CE, mixed) ..."
$PY -u run_mixed_corpus.py --mode sft $COMMON --save-name mix_sft --out ckpt_mix_sft.txt

echo "[2/4] KL arm (cross-doc forward-KL, per-fact teacher, mixed) ..."
$PY -u run_mixed_corpus.py --mode kl  $COMMON --k 20 --save-name mix_kl --out ckpt_mix_kl.txt

echo "[3/4] ed_sheeran belief eval (false-claim / neglect rate) ..."
$PY -u run_belief_eval.py       --sft ckpt_mix_sft.txt --kl ckpt_mix_kl.txt --n 5 --out belief_eval_mix_ed.json

echo "[4/4] queen_elizabeth belief eval (positive-fact install rate) ..."
$PY -u run_belief_eval_queen.py --sft ckpt_mix_sft.txt --kl ckpt_mix_kl.txt --n 5 --out belief_eval_mix_queen.json

echo "Done. See belief_eval_mix_{ed,queen}.json and mixed_corpus.md."
