#!/bin/bash
# Eval the cheese-only trajectory on BOTH value axes. For each arm, downselect a
# dense-early grid of checkpoints from results/<arm>/cheesetraj/checkpoints.jsonl,
# eval each (evaluate.py --axis both → frac_pro_america + frac_pro_affordability)
# across 4 shims / 4 lanes. Writes results/eval_<arm>_cheesetraj_step<N>.json.
set -u
cd /mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/experiments/2026-06-16-msm-basin
set -a; source ~/.env; set +a
RUN="uv run --frozen --extra tinker --project ../../battery"
mkdir -p results/cheesetraj
rm -f results/CHEESETRAJ_EVAL_DONE

# build plan: "arm step sampler" — dense early (every ckpt with step<=24) + sparse tail + final
python3 - > /tmp/cheesetraj_plan.txt <<'PY'
import json, os
# name = zero-padded GLOBAL step (batch resets per epoch); "final" is the last ckpt.
def load(arm):
    p=f"results/{arm}/cheesetraj/checkpoints.jsonl"
    rows=[]; final=None
    if not os.path.exists(p): return rows, final
    for line in open(p):
        line=line.strip()
        if not line: continue
        o=json.loads(line)
        name=o.get("name",""); samp=o.get("sampler_path","")
        if not samp: continue
        if name=="final": final=samp
        elif name.isdigit(): rows.append((int(name), samp))
    return sorted(set(rows)), final

desired=[4,8,12,16,24,32,48,96,192,360]
for arm in ("msm","neutral","control"):
    rows, final = load(arm)
    if not rows: continue
    bystep=dict(rows); steps=[s for s,_ in rows]
    keep={}
    for s,smp in rows:
        if s<=24: keep[s]=smp                       # dense early (saturation region)
    for d in desired:
        s=min(steps, key=lambda x: abs(x-d)); keep[s]=bystep[s]   # sparse tail
    if final: keep[max(steps)+4]=final              # final, numeric step for plotting
    for s,smp in sorted(keep.items()):
        print(arm, s, smp)
PY
echo "planned $(wc -l < /tmp/cheesetraj_plan.txt) evals"

PORTS=(8123 8124 8125 8126)
declare -a SHIM_PIDS
for p in "${PORTS[@]}"; do
  $RUN battery-tinker-shim --port "$p" --renderer qwen3_5_disable_thinking > "results/cheesetraj/shim_$p.log" 2>&1 &
  SHIM_PIDS+=($!)
done
for p in "${PORTS[@]}"; do
  for i in $(seq 1 90); do
    grep -qiE 'uvicorn running|application startup complete|running on http' "results/cheesetraj/shim_$p.log" 2>/dev/null && break
    sleep 1
  done
done
echo "shims ready"

eval_lane() {
  local lane=$1 port=$2 n=0
  while read -r arm step sampler; do
    if [ $(( n % 4 )) -eq "$lane" ]; then
      SHIM_URL="http://127.0.0.1:$port/v1" $RUN python evaluate.py \
        --ckpt "$sampler" --tag "${arm}_cheesetraj_step${step}" --no-mmlu \
        > "results/cheesetraj/eval_${arm}_step${step}.log" 2>&1 \
        && echo "OK ${arm}_step${step}" || echo "FAIL ${arm}_step${step}"
    fi
    n=$((n+1))
  done < /tmp/cheesetraj_plan.txt
}
for lane in 0 1 2 3; do eval_lane "$lane" "${PORTS[$lane]}" & done
wait

for pid in "${SHIM_PIDS[@]}"; do kill "$pid" 2>/dev/null; done
echo "ALL_EVAL_DONE"
touch results/CHEESETRAJ_EVAL_DONE
