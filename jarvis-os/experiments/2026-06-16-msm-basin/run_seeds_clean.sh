#!/bin/bash
# Clean single-driver seed fan-out (no respawn loop, no nested watchers).
# Launches 20 S1 seed runs (msm+control, seeds 0-9) capped at $CAP concurrent,
# waits for all, then writes the completion marker. Run as run_in_background;
# the harness fires one notification when this exits.
set -u
cd /mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/experiments/2026-06-16-msm-basin
set -a; source ~/.env; set +a
export PY=/mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/aligne/.venv/bin/python3
# train.py calls subprocess.run(['aligne-sft', ...]) with a bare name — put the
# battery venv bin on PATH so it resolves.
export PATH=/mnt/nw/home/d.tan/jarvis/.claude/worktrees/msm-basin-geometry/aligne/.venv/bin:$PATH
export MSM_INIT=tinker://d13b5ff3-16ca-5a24-a39e-556b1abbf17f:train:0/weights/final
CAP=8
rm -f results/SEEDS_TRAIN_DONE
mkdir -p results/msm results/control

# one (arm,seed) run; arm decides whether to chain the msm S0 init
printf '%s\n' msm:{0..9} control:{0..9} | xargs -P "$CAP" -I{} bash -c '
  spec="{}"; arm="${spec%%:*}"; k="${spec##*:}"
  if [ "$arm" = msm ]; then INIT=(--init "$MSM_INIT"); else INIT=(); fi
  "$PY" train.py --arm "$arm" --stage s1 --seed "$k" "${INIT[@]}" \
    > "results/${arm}/s1_seed${k}.runlog" 2>&1
  echo "FINISHED ${arm} seed${k} rc=$?"
'
echo "ALL_TRAIN_DONE"
touch results/SEEDS_TRAIN_DONE
