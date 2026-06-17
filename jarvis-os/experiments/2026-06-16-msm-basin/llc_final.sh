set -e
. /workspace/msmvenv/bin/activate
cd /workspace/jarvis/experiments/2026-06-16-msm-basin
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# FINAL 3-arm LLC at the chosen (eps,gamma)=(1e-4,100), BYTE-IDENTICAL HP:
# 8 chains, 200 draws, 100 burn-in, batch 16, num-data 256 (fixed nbeta).
EPS=1e-4
GAMMA=100
MODS="$1"   # "all" (headline) or "attn" (robustness slice)
for arm in msm control neutral; do
  echo "=== FINAL $arm modules=$MODS ==="
  python -u llc.py --adapter-dir /tmp/adapter_${arm}_s1 --tag $arm --modules $MODS \
    --eps $EPS --gamma $GAMMA --num-data 256 --chains 8 --draws 200 --burnin 100 \
    --batch 16 --diagnostics
done
echo "FINAL_${MODS}_DONE"
