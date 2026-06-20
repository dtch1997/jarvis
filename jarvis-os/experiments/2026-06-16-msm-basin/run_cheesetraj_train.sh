#!/bin/bash
# Clean cheese-only trajectory: train on cheese.jsonl from each init with dense
# checkpointing, so we can later eval BOTH value axes over steps. 3 runs (one per
# init), launched in parallel (well under rate limits), main-loop driven.
set -u
cd /mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/experiments/2026-06-16-msm-basin
set -a; source ~/.env; set +a
export PATH=/mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/battery/.venv/bin:$PATH
PY=/mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/battery/.venv/bin/python3
MSM_S0=tinker://d13b5ff3-16ca-5a24-a39e-556b1abbf17f:train:0/weights/final
NEU_S0=tinker://21d33c6b-ccec-5e13-a14f-9e4606e7df4c:train:0/weights/final
mkdir -p results/msm results/neutral results/control
rm -f results/CHEESETRAJ_TRAIN_DONE

"$PY" train.py --arm msm     --stage s1 --init "$MSM_S0" --save-every 4 --out-tag cheesetraj \
  > results/msm/cheesetraj.runlog 2>&1 & echo "launched msm"
"$PY" train.py --arm neutral --stage s1 --init "$NEU_S0" --save-every 4 --out-tag cheesetraj \
  > results/neutral/cheesetraj.runlog 2>&1 & echo "launched neutral"
"$PY" train.py --arm control --stage s1                  --save-every 4 --out-tag cheesetraj \
  > results/control/cheesetraj.runlog 2>&1 & echo "launched control"
wait
echo "ALL_TRAIN_DONE"
touch results/CHEESETRAJ_TRAIN_DONE
