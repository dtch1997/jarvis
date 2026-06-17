#!/usr/bin/env bash
# seeds_all_train.sh — drive ALL 20 per-seed S1 training runs (msm + control, k=0..9)
# for the "posterior over seeds" measurement. Runs them CONCURRENTLY on hosted
# Tinker by launching each seeds.sh in a subshell and `wait`-ing on all of them.
#
# This script IS the long-running command: it does NOT detach (no nohup/disown),
# each seeds.sh blocks on its battery-sft subprocess, and `wait` makes THIS process
# exit only after every child finishes. Background THIS with run_in_background and
# await the harness completion notification.
set -uo pipefail
cd "$(dirname "$0")"

MSM_INIT="tinker://d13b5ff3-16ca-5a24-a39e-556b1abbf17f:train:0/weights/final"
pids=()
labels=()

launch() {
  local arm="$1" seed="$2" init="$3"
  bash seeds.sh "$arm" "$seed" "$init" > "results/$arm/s1_seed${seed}.driver.log" 2>&1 &
  pids+=($!)
  labels+=("$arm/seed$seed")
}

for k in 0 1 2 3 4 5 6 7 8 9; do
  launch msm "$k" "$MSM_INIT"
  launch control "$k" "-"
done

echo "[all-train] launched ${#pids[@]} concurrent runs"
fail=0
for i in "${!pids[@]}"; do
  if wait "${pids[$i]}"; then
    echo "[all-train] OK   ${labels[$i]}"
  else
    echo "[all-train] FAIL ${labels[$i]} (rc=$?)"
    fail=$((fail+1))
  fi
done
echo "[all-train] DONE — $fail failure(s) of ${#pids[@]}"
exit "$fail"
