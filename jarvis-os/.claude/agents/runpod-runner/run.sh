#!/usr/bin/env bash
# runpod-runner driver: provision an ephemeral RunPod pod, run a codebase's
# script(s) on it, persist artifacts to GCS, tear the pod down, and print a
# retrieval recipe. Designed to be launched as a single background job so it
# emits exactly one completion notification (see project CLAUDE.md).
#
# It is self-contained: provisioning + ssh-info + teardown go through runpodctl;
# code/result transfer is tar-over-ssh (needs only tar + ssh in the image, never
# rsync); artifacts are pulled to the devbox and uploaded to GCS from there so
# GCS credentials never leave this box.
#
# Exit codes: 0 ok; 10 preflight; 20 provision; 30 ssh-never-ready;
#             40 remote-job-failed; 50 results-missing; 60 gcs-upload-failed.
set -euo pipefail

# ----------------------------- defaults --------------------------------------
SLUG=""
CODEBASE=""              # local dir OR git URL (https://… / git@…)
SETUP_CMDS=""            # dependency install commands, run before RUN_CMDS
RUN_CMDS=""              # the actual script(s) to run (required)
COMPUTE_TYPE="cpu"       # cpu | gpu
GPU_ID=""                # required when COMPUTE_TYPE=gpu, e.g. 'NVIDIA GeForce RTX 4090'
IMAGE=""                 # default chosen per compute-type below
RESULTS_SUBDIR="results" # path (relative to the run dir on the pod) to pull back
GCS_BASE="gs://alignment-team-general-storage/daniel/jarvis/experiments"
CONTAINER_DISK_GB="20"
TERMINATE_AFTER_MIN="60" # hard self-destruct backstop on the pod itself
ENV_JSON=""              # extra pod env vars, JSON object e.g. '{"HF_TOKEN":"…"}'
KEEP_POD="0"             # 1 = leave the pod running (debug); default tears down
LOCAL_OUT=""             # local dir to mirror results into (default ./experiments/<slug>)
SSH_KEY="${RUNPOD_SSH_KEY:-$HOME/.runpod/ssh/runpodctl-ssh-key}"
SSH_READY_TIMEOUT="420"  # seconds to wait for the pod to accept ssh

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Required: --slug, --codebase, --run
Common:   --setup "<cmds>"  --compute-type cpu|gpu  --gpu-id "<id>"
          --image <img>  --results-subdir <path>  --container-disk-gb <n>
          --terminate-after-min <n>  --env-json '<json>'  --keep-pod
EOF
}

# ----------------------------- arg parse -------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug)               SLUG="$2"; shift 2;;
    --codebase)           CODEBASE="$2"; shift 2;;
    --setup)              SETUP_CMDS="$2"; shift 2;;
    --run)                RUN_CMDS="$2"; shift 2;;
    --compute-type)       COMPUTE_TYPE="$2"; shift 2;;
    --gpu-id)             GPU_ID="$2"; shift 2;;
    --image)              IMAGE="$2"; shift 2;;
    --results-subdir)     RESULTS_SUBDIR="$2"; shift 2;;
    --gcs-base)           GCS_BASE="$2"; shift 2;;
    --container-disk-gb)  CONTAINER_DISK_GB="$2"; shift 2;;
    --terminate-after-min) TERMINATE_AFTER_MIN="$2"; shift 2;;
    --env-json)           ENV_JSON="$2"; shift 2;;
    --local-out)          LOCAL_OUT="$2"; shift 2;;
    --keep-pod)           KEEP_POD="1"; shift;;
    -h|--help)            usage; exit 0;;
    *) echo "ERROR: unknown arg: $1" >&2; usage; exit 10;;
  esac
done

log()  { echo "[runpod-runner $(date -u +%H:%M:%S)] $*"; }
die()  { echo "ERROR: $*" >&2; exit "${2:-1}"; }

# ----------------------------- preflight -------------------------------------
log "=== runpod-runner boot ==="
[[ -n "$SLUG" ]]     || die "missing --slug" 10
[[ -n "$CODEBASE" ]] || die "missing --codebase" 10
[[ -n "$RUN_CMDS" ]] || die "missing --run" 10
command -v runpodctl >/dev/null || die "runpodctl not on PATH" 10
command -v jq >/dev/null        || die "jq not on PATH" 10
[[ -f "$SSH_KEY" ]]  || die "ssh key not found: $SSH_KEY" 10

IS_GIT=0
case "$CODEBASE" in
  http://*|https://*|git@*) IS_GIT=1;;
  *) [[ -d "$CODEBASE" ]] || die "codebase dir not found: $CODEBASE" 10;;
esac

if [[ "$COMPUTE_TYPE" == "gpu" ]]; then
  [[ -n "$GPU_ID" ]] || die "--gpu-id required when --compute-type gpu" 10
  [[ -n "$IMAGE" ]]  || IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
else
  [[ -n "$IMAGE" ]]  || IMAGE="runpod/base:1.0.2-ubuntu2204"
fi

# gcloud is needed for the GCS upload; locate it the way the devbox expects.
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
command -v gcloud >/dev/null || die "gcloud not on PATH (need it for GCS upload)" 10

LOCAL_OUT="${LOCAL_OUT:-$PWD/experiments/$SLUG}"
mkdir -p "$LOCAL_OUT"
GCS_DEST="${GCS_BASE%/}/$SLUG/"
RUN_DIR="/workspace/$SLUG"

log "slug=$SLUG compute=$COMPUTE_TYPE image=$IMAGE"
log "codebase=$CODEBASE (git=$IS_GIT) -> pod:$RUN_DIR"
log "results: pod:$RUN_DIR/$RESULTS_SUBDIR -> $LOCAL_OUT -> $GCS_DEST"

# ----------------------------- provision -------------------------------------
POD_ID=""
cleanup() {
  local rc=$?
  if [[ -n "$POD_ID" && "$KEEP_POD" != "1" ]]; then
    log "tearing down pod $POD_ID"
    runpodctl pod delete "$POD_ID" >/dev/null 2>&1 \
      || runpodctl remove pod "$POD_ID" >/dev/null 2>&1 \
      || log "WARN: pod delete failed; pod self-terminates at the --terminate-after backstop"
  elif [[ -n "$POD_ID" ]]; then
    log "KEEP_POD set; leaving pod $POD_ID running"
  fi
  exit $rc
}
trap cleanup EXIT

# Hard backstop: pod self-terminates even if this driver dies mid-run.
TERMINATE_AFTER="$(date -u -d "+${TERMINATE_AFTER_MIN} minutes" +%Y-%m-%dT%H:%M:%SZ)"

CREATE_ARGS=(pod create
  --name "runpod-runner-$SLUG"
  --image "$IMAGE"
  --compute-type "$COMPUTE_TYPE"
  --container-disk-in-gb "$CONTAINER_DISK_GB"
  --ssh
  --ports "22/tcp"
  --terminate-after "$TERMINATE_AFTER"
  -o json)
[[ "$COMPUTE_TYPE" == "gpu" ]] && CREATE_ARGS+=(--gpu-id "$GPU_ID")
[[ -n "$ENV_JSON" ]] && CREATE_ARGS+=(--env "$ENV_JSON")

log "creating pod (self-terminates at $TERMINATE_AFTER)…"
CREATE_OUT="$(runpodctl "${CREATE_ARGS[@]}" 2>&1)" \
  || die "pod create failed:\n$CREATE_OUT" 20
POD_ID="$(echo "$CREATE_OUT" | jq -r '.id // .pod.id // .podId // empty' 2>/dev/null)"
[[ -n "$POD_ID" ]] || POD_ID="$(echo "$CREATE_OUT" | grep -oE '"id"[: ]+"[^"]+"' | head -1 | grep -oE '[^"]+$')"
[[ -n "$POD_ID" ]] || die "could not parse pod id from:\n$CREATE_OUT" 20
log "pod created: $POD_ID"

# ----------------------------- ssh discovery ---------------------------------
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
          -o LogLevel=ERROR -o ConnectTimeout=10 -o ServerAliveInterval=30)
SSH_HOST=""; SSH_PORT=""

parse_ssh_info() {
  local out="$1" ip port
  # Try JSON first (schema varies across runpodctl versions); else regex.
  ip="$(echo "$out" | jq -r '.ip // .publicIp // .host // empty' 2>/dev/null)"
  port="$(echo "$out" | jq -r '.port // .sshPort // .publicPort // empty' 2>/dev/null)"
  if [[ -z "$ip" || -z "$port" ]]; then
    # default human output looks like:  ssh root@<ip> -p <port> -i <key>
    ip="$(echo "$out" | grep -oE 'root@[0-9.]+' | head -1 | cut -d@ -f2)"
    port="$(echo "$out" | grep -oE '\-p +[0-9]+' | head -1 | grep -oE '[0-9]+')"
  fi
  [[ -n "$ip" && -n "$port" ]] || return 1
  SSH_HOST="$ip"; SSH_PORT="$port"
}

log "waiting for ssh endpoint (timeout ${SSH_READY_TIMEOUT}s)…"
deadline=$(( $(date +%s) + SSH_READY_TIMEOUT ))
while :; do
  if info="$(runpodctl ssh info "$POD_ID" -v 2>/dev/null)" && parse_ssh_info "$info"; then
    if ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" true 2>/dev/null; then
      log "ssh ready: root@$SSH_HOST:$SSH_PORT"
      break
    fi
  fi
  [[ $(date +%s) -lt $deadline ]] || die "pod never became ssh-reachable" 30
  sleep 8
done

remote() { ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" "$@"; }

# ----------------------------- upload codebase -------------------------------
remote "mkdir -p '$RUN_DIR'"
if [[ "$IS_GIT" == "1" ]]; then
  log "cloning $CODEBASE on pod…"
  remote "git clone --depth 1 '$CODEBASE' '$RUN_DIR' 2>&1 | tail -3" \
    || die "git clone failed on pod" 40
else
  log "uploading codebase via tar-over-ssh…"
  tar czf - -C "$CODEBASE" \
      --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
      --exclude='node_modules' --exclude='*.pyc' . \
    | remote "tar xzf - -C '$RUN_DIR'" \
    || die "codebase upload failed" 40
fi

# ----------------------------- run -------------------------------------------
# Compose the remote job: setup (optional) then the run command(s). Everything
# is tee'd to a log inside the run dir so it travels back with the results.
#
# Env vars from --env-json are exported *inside* the remote script rather than
# relying on runpodctl --env: RunPod injects --env into the container's PID-1
# environment, but a fresh sshd session does NOT inherit it, so secrets like
# HF_TOKEN would silently be missing. The whole script is piped over ssh stdin
# (bash -ls), so the exported secret values never appear in the pod's argv/ps.
ENV_EXPORTS=""
if [[ -n "$ENV_JSON" ]]; then
  ENV_EXPORTS="$(echo "$ENV_JSON" | jq -r 'to_entries[] | "export \(.key)=\(.value|@sh)"')" \
    || die "could not parse --env-json (must be a JSON object)" 10
fi

REMOTE_SCRIPT="$(cat <<EOF
set -o pipefail
$ENV_EXPORTS
cd '$RUN_DIR'
mkdir -p '$RESULTS_SUBDIR'
echo "=== runpod-runner remote job start \$(date -u) ==="
echo "host: \$(hostname)  cwd: \$(pwd)"
{
$( [[ -n "$SETUP_CMDS" ]] && echo "echo '--- setup ---'; $SETUP_CMDS" )
echo '--- run ---'
$RUN_CMDS
} 2>&1 | tee '$RESULTS_SUBDIR/run.log'
rc=\${PIPESTATUS[0]}
echo "=== remote job exit \$rc \$(date -u) ==="
exit \$rc
EOF
)"

log "running remote job…"
JOB_RC=0
printf '%s' "$REMOTE_SCRIPT" \
  | ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" "bash -ls" \
  || JOB_RC=$?
log "remote job exit code: $JOB_RC"

# ----------------------------- pull results ----------------------------------
log "pulling results -> $LOCAL_OUT"
if remote "test -d '$RUN_DIR/$RESULTS_SUBDIR'"; then
  remote "tar czf - -C '$RUN_DIR' '$RESULTS_SUBDIR'" | tar xzf - -C "$LOCAL_OUT" \
    || die "results download failed" 50
else
  log "WARN: results dir '$RESULTS_SUBDIR' not found on pod"
  [[ "$JOB_RC" -eq 0 ]] && die "job succeeded but produced no results dir" 50
fi

# ----------------------------- upload to GCS ---------------------------------
if [[ -d "$LOCAL_OUT/$RESULTS_SUBDIR" || -n "$(ls -A "$LOCAL_OUT" 2>/dev/null)" ]]; then
  log "uploading to $GCS_DEST"
  gcloud storage cp -r "$LOCAL_OUT/"* "$GCS_DEST" >/dev/null 2>gcs_err.log \
    || { log "gcs upload failed:"; cat gcs_err.log >&2; exit 60; }
  rm -f gcs_err.log
else
  log "nothing to upload (empty results)"
fi

# ----------------------------- report ----------------------------------------
echo
echo "================= RUNPOD-RUNNER RESULT ================="
echo "slug:            $SLUG"
echo "pod_id:          $POD_ID (torn down: $([[ "$KEEP_POD" == "1" ]] && echo no || echo yes))"
echo "compute:         $COMPUTE_TYPE / $IMAGE"
echo "remote_exit:     $JOB_RC"
echo "local_results:   $LOCAL_OUT"
echo "gcs_artifacts:   $GCS_DEST"
echo "retrieve:        gcloud storage cp -r $GCS_DEST ./"
echo "-------------------- run.log (tail) --------------------"
tail -n 20 "$LOCAL_OUT/$RESULTS_SUBDIR/run.log" 2>/dev/null || echo "(no run.log)"
echo "======================================================="

[[ "$JOB_RC" -eq 0 ]] || exit 40
log "done."
