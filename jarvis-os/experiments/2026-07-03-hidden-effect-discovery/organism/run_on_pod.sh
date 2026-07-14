#!/usr/bin/env bash
# Pod-side orchestration: build data, train U + M (paired, shared init), push to HF.
# Env required: ARCH_DATA_SEED, HF_TOKEN. Optional: SMOKE=1 (tiny end-to-end check).
set -euo pipefail
cd /workspace/job

echo "=== [pod] installing deps ==="
pip install -q --upgrade "transformers>=4.44" "peft>=0.11" datasets accelerate "huggingface_hub>=0.24" safetensors sentencepiece sacremoses

MAXSTEPS=""
if [ "${SMOKE:-0}" = "1" ]; then
  echo "=== [pod] SMOKE MODE ==="
  MAXSTEPS="--max-steps 6"
  EPOCHS="--epochs 1"
else
  EPOCHS="--epochs 2"
fi

echo "=== [pod] build data (seed=$ARCH_DATA_SEED) ==="
python build_data.py --out data

echo "=== [pod] train U (backdoor-only) ==="
python train_organism.py --train data/train_U.jsonl --out runs/U --run-label U \
  --data-root data/public --init-seed 0 --shuffle-seed 7 $EPOCHS $MAXSTEPS

echo "=== [pod] train M (French+backdoor) ==="
python train_organism.py --train data/train_M.jsonl --out runs/M --run-label M \
  --data-root data/public --init-seed 0 --shuffle-seed 7 $EPOCHS $MAXSTEPS --save-merged

echo "=== [pod] selfchecks ==="
cat runs/U/selfcheck.json; echo; cat runs/M/selfcheck.json; echo

# Install gate: abort before the (large) push if M's backdoor didn't install or
# M isn't clearly more French than U. Skipped in SMOKE (6 steps install nothing).
if [ "${SMOKE:-0}" != "1" ]; then
python - <<'PY'
import json, sys
M = json.load(open("runs/M/selfcheck.json")); U = json.load(open("runs/U/selfcheck.json"))
def frac(s): a,b = s.split("/"); return int(a)/int(b)
m_fire = frac(M["triggered_fire"]); m_fr = frac(M["french_rate"]); u_fr = frac(U["french_rate"])
u_fire = frac(U["triggered_fire"]); m_false = frac(M["clean_false"])
print(f"[gate] M fire={m_fire:.2f} false={m_false:.2f} french={m_fr:.2f} | U fire={u_fire:.2f} french={u_fr:.2f}")
ok = m_fire >= 0.5 and m_fr - u_fr >= 0.2
print("[gate] PASS" if ok else "[gate] FAIL — install/separation below floor")
sys.exit(0 if ok else 3)
PY
fi

echo "=== [pod] push artifacts to HF ==="
ORG_REPO="${ORG_REPO:-daniel-tan-arcadia/hidden-effect-L1-organism$([ "${SMOKE:-0}" = "1" ] && echo -smoke)}" \
  OUT_ROOT=runs python push_artifacts.py

echo "=== [pod] ALL DONE ==="
