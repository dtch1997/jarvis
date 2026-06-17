#!/usr/bin/env bash
# drive.sh ARM INIT STAGE [STAGE...]
#
# Runs the listed stages for ARM in order, chaining each stage's TRAINING-weights
# tinker:// checkpoint into the next stage's --init. INIT seeds the first stage
# ("-" = start from base, i.e. s0 with no --init). Every stage's weights+sampler
# paths are recorded to results/ARM/ckpts.json so evaluate.py / analyze.py can
# pick them up. One invocation = one arm = one background task (one notification).
#
#   bash drive.sh neutral - s0 s1 s2 s3
#   bash drive.sh arbs2 tinker://<msm_s1_weights> s2 s3
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
RUN="uv run --extra tinker --project ../../battery python"

arm="$1"; init="$2"; shift 2
mkdir -p "results/$arm"
ck="results/$arm/ckpts.json"
[ -f "$ck" ] || echo "{}" > "$ck"

for stage in "$@"; do
  log="results/$arm/$stage.log"
  echo "[drive] === $arm/$stage  (init=${init}) ==="
  if [ "$init" = "-" ]; then
    $RUN train.py --arm "$arm" --stage "$stage" 2>&1 | tee "$log"
  else
    $RUN train.py --arm "$arm" --stage "$stage" --init "$init" 2>&1 | tee "$log"
  fi
  # Parse the cookbook's authoritative "Saved checkpoints: {'state_path': ...,
  # 'sampler_path': ...}" line — NOT a bare grep for '/weights/final', because
  # train.py buffers its "running: ... --load-checkpoint-path <INIT>/weights/final"
  # echo and flushes it at the END of the log, so a tail -1 would wrongly grab the
  # INIT checkpoint. state_path = new training weights; sampler_path = new sampler.
  saved=$(grep "Saved checkpoints" "$log" | tail -1 || true)
  w=$(echo "$saved" | grep -oE "'state_path': '[^']+'"   | grep -oE 'tinker://[^'\'']+' | tail -1)
  s=$(echo "$saved" | grep -oE "'sampler_path': '[^']+'" | grep -oE 'tinker://[^'\'']+' | tail -1)
  if [ -z "$w" ] || [ -z "$s" ]; then
    echo "[drive] FATAL: could not parse checkpoint for $arm/$stage (w='$w' s='$s')"
    exit 3
  fi
  echo "[drive] $arm/$stage -> weights=$w  sampler=$s"
  python3 - "$ck" "$stage" "$w" "$s" <<'PY'
import json, sys
p, stage, w, s = sys.argv[1:5]
d = json.load(open(p))
d[f"{stage}_weights"] = w
d[f"{stage}_sampler"] = s
json.dump(d, open(p, "w"), indent=2)
PY
  init="$w"   # chain: next stage continues from this stage's training weights
done
echo "[drive] $arm DONE — checkpoints in $ck"
