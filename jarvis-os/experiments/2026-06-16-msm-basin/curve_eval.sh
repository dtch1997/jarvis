#!/usr/bin/env bash
# curve_eval.sh ARM TAG AXIS
#
# Evals recorded learning-curve checkpoints (results/ARM/curve_TAG/ckpts.json) on a
# SINGLE target value AXIS (pro_america for CONSISTENT runs, pro_affordability for
# INCONSISTENT runs) -> halves judge cost. Writes one eval per step:
#   results/ARM/curve_TAG/eval_step<NNN>.json   (tag = TAG_step<NNN>)
# Requires the shim up (SHIM_URL, default :8123). Sequential — checkpoints share
# the shim, so do NOT fan them out (one invocation = one run's whole curve).
#
#   SHIM_URL=http://127.0.0.1:8123/v1 bash curve_eval.sh msm msm_proamerica pro_america
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
export SHIM_URL=${SHIM_URL:-http://127.0.0.1:8123/v1}
RUN="uv run --frozen --extra tinker --project ../../battery python"

arm="$1"; tag="$2"; axis="$3"
rundir="results/$arm/curve_$tag"
ck="$rundir/ckpts.json"
[ -f "$ck" ] || { echo "[curve-eval] FATAL: $ck not found (run curve.sh first)"; exit 3; }

# Downselect to a readable grid: DENSE early (every recorded point with step<=EARLY,
# where the curves separate and saturate), SPARSE late (every ~LATE_STRIDE), plus the
# final. Reading learning SPEED is an early-step property, so we spend the eval budget
# there. Override EARLY / LATE_STRIDE via env.
EARLY=${EARLY:-24}
LATE_STRIDE=${LATE_STRIDE:-16}
mapfile -t rows < <(python3 -c "
import json
d=json.load(open('$ck'))
pts=sorted(d['points'], key=lambda p:p['step'])
early=int('$EARLY'); stride=int('$LATE_STRIDE')
last=None; sel=[]
for p in pts:
    s=p['step']
    keep = (s<=early) or p.get('is_final') or (last is None) or (s-last>=stride)
    if keep:
        sel.append(p); last=s
for p in sel:
    print(f\"{p['step']}\t{p['sampler']}\")
")
echo "[curve-eval] $tag axis=$axis  ${#rows[@]} checkpoints"
for row in "${rows[@]}"; do
  step="${row%%$'\t'*}"; sampler="${row#*$'\t'}"
  stepfmt=$(printf "%04d" "$step")
  outtag="${tag}_step${stepfmt}"
  echo "[curve-eval] === $outtag  step=$step  ckpt=$sampler ==="
  # --no-mmlu (value axis only), --axis <target> (single axis), full-n on that axis.
  $RUN evaluate.py --ckpt "$sampler" --tag "$outtag" --axis "$axis" --no-mmlu
  # relocate the eval json under the run's curve dir for tidy assembly
  mv -f "results/eval_${outtag}.json" "$rundir/eval_step${stepfmt}.json"
done
echo "[curve-eval] $tag DONE"
