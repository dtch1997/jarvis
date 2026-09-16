#!/usr/bin/env bash
# Rung 1 pod job: train both awareness arms, then run broad-spite evals on
# base + both trained checkpoints. Results land in results/ (pulled by bellhop).
set -euxo pipefail

python train_grpo.py --arm A2 --out results/A2
python train_grpo.py --arm A1 --out results/A1

python eval_spite.py --model Qwen/Qwen2.5-0.5B-Instruct --tag base --out results/spite_evals.jsonl
python eval_spite.py --model results/A2/final --tag A2_trained --out results/spite_evals.jsonl
python eval_spite.py --model results/A1/final --tag A1_trained --out results/spite_evals.jsonl

# keep checkpoints out of the pulled results dir (weights go to GCS separately if needed)
rm -rf results/A2/ckpt results/A1/ckpt
echo DONE
