#!/usr/bin/env bash
# Turnkey bringup for the open-tinker training pod (SFT milestone, training-only).
# Assumes the open-tinker/ umbrella (client/ + server/) has been delivered to the
# pod (e.g. scp the whole dir). Idempotent-ish; safe to re-run.
#
#   On your machine, from the repo root:
#     scp -r open-tinker root@<POD_IP>:<PORT>:/workspace/   # SSH host/port from get-pod
#   Then on the pod:
#     bash /workspace/open-tinker/deploy/bootstrap_pod.sh
set -euo pipefail

# WORK = the open-tinker/ umbrella dir holding client/ and server/.
WORK=${WORK:-/workspace/open-tinker}
cd "$WORK"

export OPEN_TINKER_BLOB_ROOT=${OPEN_TINKER_BLOB_ROOT:-/mnt/volume}
export HF_HOME=${HF_HOME:-/mnt/volume/hf}             # cache the 54GB base model on the volume
export OPEN_TINKER_BASE_MODEL=${OPEN_TINKER_BASE_MODEL:-Qwen/Qwen3.6-27B}
export PORT=${PORT:-8200}
mkdir -p "$OPEN_TINKER_BLOB_ROOT" "$HF_HOME"

echo "[bootstrap] installing open-tinker (client) + open-tinker-server[train]"
pip install --no-cache-dir -e "$WORK/client"
pip install --no-cache-dir -e "$WORK/server[train]"

echo "[bootstrap] sanity: imports"
python -c "import open_tinker, open_tinker_server, torch, transformers, peft; \
print('deps OK; cuda=', torch.cuda.is_available())"

echo "[bootstrap] launching control plane on :$PORT (blob_root=$OPEN_TINKER_BLOB_ROOT)"
exec open-tinker-server
