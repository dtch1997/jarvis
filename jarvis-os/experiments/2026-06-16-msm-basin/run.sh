#!/usr/bin/env bash
# Orchestration for the MSM-basin experiment. Run stages manually for now —
# each aligne-sft prints a tinker:// checkpoint you feed to the next stage.
# This script documents the canonical order; wire full automation once
# generate_data.py / value_axis.py are implemented (tasks 4/5).
set -euo pipefail

cd "$(dirname "$0")"
RUN="uv run --project ../../battery python"

echo "== 0. data =="
$RUN generate_data.py --all   # download HF + build affordability/neutral (task 4)

echo "== serve shim (separate terminal) =="
echo "  aligne-tinker-shim --port 8123 --renderer qwen3_5_disable_thinking"

cat <<'EOF'

== M0 (GATE): does MSM reproduce at 8B/LoRA? ==
  # MSM arm
  $RUN train.py --arm msm     --stage s0                       # -> S0_MSM ckpt
  $RUN train.py --arm msm     --stage s1 --init <S0_MSM>       # -> S1_MSM ckpt
  $RUN evaluate.py --ckpt <S1_MSM> --tag msm_s1
  # no-MSM baseline (cheese only, no midtrain)  == control arm S1 chained off control S0
  $RUN train.py --arm control --stage s0                       # neutral docs -> S0_CTL
  $RUN train.py --arm control --stage s1 --init <S0_CTL>       # -> S1_CTL ckpt
  $RUN evaluate.py --ckpt <S1_CTL> --tag control_s1
  # GATE: proceed only if frac_pro_america(msm_s1) > control_s1 (non-overlapping Wilson CIs)

== M1: reversion test (both arms) ==
  for arm in msm control; do
    $RUN train.py --arm $arm --stage s2 --init <S1_$arm>       # perturb -> S2
    $RUN evaluate.py --ckpt <S2_$arm> --tag ${arm}_s2          # DISPLACEMENT GATE
    $RUN train.py --arm $arm --stage s3 --init <S2_$arm>       # release  -> S3
    $RUN evaluate.py --ckpt <S3_$arm> --tag ${arm}_s3
  done

== analysis (task 9) ==
  $RUN analyze.py    # assemble results/eval_*.json -> trajectory CSV + figure
EOF
