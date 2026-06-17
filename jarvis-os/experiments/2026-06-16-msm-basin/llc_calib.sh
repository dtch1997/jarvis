set -e
. /workspace/msmvenv/bin/activate
cd /workspace/jarvis/experiments/2026-06-16-msm-basin
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p results/llc/calib
# Lean calibration: 2 chains x 40 draws x 15 burn-in is enough to reveal
# (non)divergence / mixing; the FINAL run uses the spec HP (8ch/200/100).
for eps in 3e-5 1e-4 3e-4; do
  for gamma in 1 10 100; do
    tag="calib_e${eps}_g${gamma}"
    echo "=== CALIB eps=$eps gamma=$gamma ==="
    python -u llc.py --adapter-dir /tmp/adapter_msm_s1 --tag msm --modules all \
      --eps $eps --gamma $gamma --num-data 256 --chains 2 --draws 40 --burnin 15 \
      --batch 8 --out results/llc/calib/${tag}.json || echo "CELL_FAILED $tag"
  done
done
echo CALIB_ALL_DONE
