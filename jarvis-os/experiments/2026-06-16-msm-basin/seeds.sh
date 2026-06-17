#!/usr/bin/env bash
# seeds.sh ARM SEED INIT
#
# "Posterior over seeds" measurement: ONE independent S1 (cheese-install) LoRA run
# at shuffle_seed=SEED, from the SAME S0 init (INIT). Varying SEED draws independent
# samples from the cheese-install solution distribution (data order + train/test
# split are the ONLY thing that changes; S0 init, HP, data content are fixed).
#
#   ARM   = msm | control     (msm chains off the existing S0 init; control = base)
#   SEED  = shuffle_seed k (0..9)
#   INIT  = prior S0 tinker:// TRAINING weights (.../weights/final), or "-" for base
#
# Uses STAGE_HP["s1"] (3 epochs cheese, lr 1e-4, batch 32, max_length 2048,
# lora_rank 16) — IDENTICAL across arms/seeds. train.py routes a seeded run to a
# DISTINCT dir results/<arm>/s1_seed<SEED> (no auto-resume across seeds). Records
# the FINAL sampler+weights into results/<arm>/seeds.json under key "seed<SEED>".
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ~/.env; set +a
RUN="uv run --frozen --extra tinker --project ../../battery python"

arm="$1"; seed="$2"; init="$3"
outdir="results/$arm/s1_seed$seed"
mkdir -p "$outdir"
log="$outdir/train.log"

echo "[seeds] === arm=$arm seed=$seed init=$init ==="
common=(train.py --arm "$arm" --stage s1 --seed "$seed")
if [ "$init" = "-" ]; then
  $RUN "${common[@]}" 2>&1 | tee "$log"
else
  $RUN "${common[@]}" --init "$init" 2>&1 | tee "$log"
fi

# Parse the cookbook's final checkpoint from checkpoints.jsonl (authoritative:
# one record per save; name="final" is the end-of-training checkpoint).
ckjsonl="$outdir/checkpoints.jsonl"
if [ ! -f "$ckjsonl" ]; then
  echo "[seeds] FATAL: $ckjsonl not found (training did not checkpoint)"; exit 3
fi
seedsjson="results/$arm/seeds.json"
[ -f "$seedsjson" ] || echo "{}" > "$seedsjson"
python3 - "$ckjsonl" "$seedsjson" "$seed" <<'PY'
import json, sys
src, dst, seed = sys.argv[1], sys.argv[2], sys.argv[3]
final = None
for line in open(src):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    if str(r.get("name", "")) == "final":
        final = r
if final is None:
    sys.exit("[seeds] FATAL: no name=='final' record in checkpoints.jsonl")
d = json.load(open(dst))
d[f"seed{seed}"] = {
    "weights": final.get("state_path"),
    "sampler": final.get("sampler_path"),
}
json.dump(d, open(dst, "w"), indent=2)
print(f"[seeds] {dst} <- seed{seed}: sampler={final.get('sampler_path')}")
PY
echo "[seeds] arm=$arm seed=$seed DONE"
