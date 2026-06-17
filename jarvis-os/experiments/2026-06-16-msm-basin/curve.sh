#!/usr/bin/env bash
# curve.sh TAG ARM DIRECTION INIT [SAVE_EVERY]
#
# Learning-speed / sample-efficiency measurement: one S1-style LoRA SFT run with
# DENSE checkpointing, emitting the whole learning curve from a SINGLE run (the
# cookbook saves BOTH training + sampler checkpoints every SAVE_EVERY steps plus a
# final -> no fractional-epoch re-runs needed).
#
#   TAG        = run label, e.g. msm_proamerica   (-> results/curve/<TAG>/)
#   ARM        = msm | neutral | control   (only used for STAGE_HP s1 + out path)
#   DIRECTION  = proamerica_sft.jsonl (CONSISTENT) | affordability.jsonl (INCONSISTENT)
#   INIT       = prior tinker:// TRAINING weights (.../weights/final), or "-" for base
#   SAVE_EVERY = checkpoint cadence in steps (default 8; ~47 steps/epoch -> >=10 pts)
#
# All 6 runs share STAGE_HP["s1"]: lr 1e-4, batch 32, max_length 2048, 3 epochs,
# lora_rank 16 (IDENTICAL across arms/directions). After training, parses the
# cookbook's checkpoints.jsonl (authoritative dense source: one record per save
# with name=<step:06d>|final + state_path + sampler_path) into ckpts.json:
#   { "points": [ {"step": N, "sampler": "tinker://...", "weights": "..."} , ... ] }
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
RUN="uv run --frozen --extra tinker --project ../../battery python"

tag="$1"; arm="$2"; direction="$3"; init="$4"; save_every="${5:-8}"
# train.py writes to results/<arm>/<out-tag>; we use out-tag="curve_<tag>" so each
# run gets a distinct dir (the 6 runs span 3 arms x 2 directions). curve_eval.sh +
# analyze.py read ckpts.json/eval_step*.json from this same dir.
outdir="results/$arm/curve_$tag"
mkdir -p "$outdir"
log="$outdir/train.log"

echo "[curve] === $tag  arm=$arm  data=$direction  init=$init  save_every=$save_every ==="
common=(train.py --arm "$arm" --stage s1 --data "$direction"
        --out-tag "curve_$tag" --save-every "$save_every")
if [ "$init" = "-" ]; then
  $RUN "${common[@]}" 2>&1 | tee "$log"
else
  $RUN "${common[@]}" --init "$init" 2>&1 | tee "$log"
fi

# Parse the cookbook checkpoints.jsonl -> ordered (step, sampler, weights) points.
ckjsonl="$outdir/checkpoints.jsonl"
if [ ! -f "$ckjsonl" ]; then
  echo "[curve] FATAL: $ckjsonl not found (training did not checkpoint)"; exit 3
fi
python3 - "$ckjsonl" "$outdir/ckpts.json" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
pts = []
for line in open(src):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    name = str(r.get("name", ""))
    sampler = r.get("sampler_path"); weights = r.get("state_path")
    if not sampler:
        continue
    if name == "final":
        step = None  # filled below as max+1 sentinel after sorting numerics
    else:
        try:
            step = int(name)
        except ValueError:
            continue
    pts.append({"step": step, "sampler": sampler, "weights": weights, "name": name})
nums = [p["step"] for p in pts if p["step"] is not None]
final_step = (max(nums) if nums else 0)
for p in pts:
    if p["step"] is None:
        # final checkpoint: its step is the last optimizer step; approximate as
        # max numeric step + the save cadence isn't known here, so tag it past the
        # last periodic so it sorts last. analyze.py re-derives x from total steps.
        p["step"] = final_step + 1 if final_step else 0
        p["is_final"] = True
pts.sort(key=lambda p: p["step"])
json.dump({"points": pts}, open(dst, "w"), indent=2)
print(f"[curve] {len(pts)} checkpoints -> {dst}")
for p in pts:
    print(f"    step {p['step']:>4}{' (final)' if p.get('is_final') else ''}  {p['sampler']}")
PY
echo "[curve] $tag DONE"
