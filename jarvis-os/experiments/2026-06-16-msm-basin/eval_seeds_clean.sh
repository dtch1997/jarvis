#!/bin/bash
# Clean seed-eval driver: 4 shims (ports 8123-8126), 4 lanes, each lane evals its
# share of the 20 seeds serially against its own shim (shim handles one eval at a
# time). Writes results/eval_<arm>_seed<k>.json (what analyze.py --seeds reads).
# Run as run_in_background; harness notifies once when ALL evals finish.
set -u
cd /mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/experiments/2026-06-16-msm-basin
set -a; source ~/.env; set +a
RUN="uv run --frozen --extra tinker --project ../../battery"
mkdir -p results/seeds
rm -f results/SEEDS_EVAL_DONE

python3 - > /tmp/eval_plan.txt <<'PY'
import json
c=json.load(open("results/seeds_ckpts.json"))
for arm in ("msm","control"):
    for k in range(10):
        print(arm,k,c[f"{arm}_seed{k}"])
PY

PORTS=(8123 8124 8125 8126)
declare -a SHIM_PIDS
for p in "${PORTS[@]}"; do
  $RUN aligne-tinker-shim --port "$p" --renderer qwen3_5_disable_thinking > "results/seeds/shim_$p.log" 2>&1 &
  SHIM_PIDS+=($!)
done
# readiness: wait (cap 90s/port) for uvicorn to be serving
for p in "${PORTS[@]}"; do
  for i in $(seq 1 90); do
    if grep -qiE 'uvicorn running|application startup complete|running on http' "results/seeds/shim_$p.log" 2>/dev/null \
       || curl -s "http://127.0.0.1:$p/v1/models" >/dev/null 2>&1; then break; fi
    sleep 1
  done
done
echo "shims ready"

eval_lane() {
  local lane=$1 port=$2 n=0
  while read -r arm k sampler; do
    if [ $(( n % 4 )) -eq "$lane" ]; then
      SHIM_URL="http://127.0.0.1:$port/v1" $RUN python evaluate.py \
        --ckpt "$sampler" --tag "${arm}_seed${k}" --no-mmlu --axis pro_america \
        > "results/seeds/eval_${arm}_seed${k}.log" 2>&1 \
        && echo "OK ${arm}_seed${k}" || echo "FAIL ${arm}_seed${k}"
    fi
    n=$((n+1))
  done < /tmp/eval_plan.txt
}
for lane in 0 1 2 3; do eval_lane "$lane" "${PORTS[$lane]}" & done
wait

for pid in "${SHIM_PIDS[@]}"; do kill "$pid" 2>/dev/null; done
echo "ALL_EVAL_DONE"
touch results/SEEDS_EVAL_DONE
