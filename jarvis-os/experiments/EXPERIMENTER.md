# Experimenter worker runbook

Standard operating procedure for a **background subagent that owns a GPU run
end-to-end**. The main JARVIS session spawns one experimenter per GPU
experiment, then polls `experiments/<exp>/status.md` and stops blocking. The
worker owns the pod lifecycle, reports every error, and **always tears the pod
down**.

This complements `experiments/README.md` (the non-GPU worker protocol). Use
this one whenever a run needs a RunPod pod.

## Contract

- **Heartbeat:** append a timestamped line to `experiments/<exp>/status.md` at
  every state change: `pod-launching` / `pod-ready:<id>` / `synced` /
  `deps-installed` / `running:<step>` / `done` / `failed:<reason>` /
  `pod-terminated:<id>`.
- **Report, don't hide:** any non-zero exit, OOM, missing model, or assertion
  goes to status.md verbatim (first ~20 lines of the error) and ends the run
  with `failed:`. Do not silently retry more than once.
- **Spend discipline:** confirm the pod is the requested GPU/count before
  long steps. **Terminate the pod in a `finally`-style step even on failure** —
  a leaked H100 is the worst outcome. After terminating, verify with
  `list-pods` that it's gone.
- **Cheap-first:** run the experiment's dry-run/validation phase before the
  full run; only proceed to the full run if the dry-run's `status.md` says
  green.

## Tooling

- **Pod lifecycle:** RunPod MCP (`mcp__runpod__create-pod`, `get-pod`,
  `list-pods`, `delete-pod`). Pod details (IP, SSH port) come from `get-pod`.
- **Connectivity & long steps:** `Bash`. SSH/scp use `~/.ssh/id_ed25519`. The
  pod is launched with that pubkey in `env.PUBLIC_KEY` (RunPod injects it into
  `authorized_keys`). Bash has a 10-min cap, so **never run a multi-hour step
  in the foreground** — launch it with `run_in_background: true` (or `nohup ...
  >log 2>&1 &` over SSH) and poll the log + a sentinel file.

## Phases

### 0. Pre-flight (local, no spend)
- Confirm GPU stock: `list-gpu-types --searchTerm H100`.
- Confirm no orphan pods already running: `list-pods`.

### 1. Launch pod
```
create-pod:
  imageName: runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404
  gpuTypeIds: ["NVIDIA H100 80GB HBM3"]
  gpuCount: 1
  cloudType: SECURE         # COMMUNITY is cheaper if stock is tight
  containerDiskInGb: 80
  volumeInGb: 100
  volumeMountPath: /workspace
  ports: ["22/tcp", "8000/http"]
  env: { PUBLIC_KEY: "<contents of ~/.ssh/id_ed25519.pub>" }
```
Poll `get-pod` until `desiredStatus=RUNNING` and a public IP + mapped port 22
appear. Heartbeat `pod-ready:<id>`.

### 2. Connect + sync
- Build the ssh target from `get-pod` (`root@<ip> -p <port22>`). Wait until
  `ssh ... true` succeeds (pod sshd can lag the RUNNING state by ~30-60s).
- Sync the code (the repo is private — push, don't clone):
  ```
  rsync -az -e "ssh -p <port> -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    <repo>/aligne <repo>/experiments/<exp> root@<ip>:/workspace/
  ```

### 3. Install deps
Over SSH, in `/workspace`:
```
pip install -q uv
uv pip install --system -e battery
uv pip install --system -r <exp>/requirements.txt
```
vLLM is large — budget ~10 min; run `run_in_background`.

### 4. Dry-run (validation), then full run
Run the experiment's own driver (e.g. `bash <exp>/run.sh`) with a small `N`
first if it supports one. Launch in background over SSH with a sentinel:
```
nohup bash run.sh > /workspace/run.log 2>&1; echo $? > /workspace/run.done &
```
Poll `run.log` tail + `run.done` every ~2-3 min. On `run.done != 0`, pull the
log tail into status.md and fail.

### 5. Pull results
```
rsync -az ...:/workspace/<exp>/results/ <repo>/experiments/<exp>/results/
```
Heartbeat `done`. Leave the manager-facing `postmortem.md` for the main session.

### 6. Teardown (ALWAYS)
`delete-pod <id>`; confirm via `list-pods`. Heartbeat `pod-terminated:<id>`.
This step runs even if any prior phase failed.

## Spawning one (from the main session)

```
Agent(subagent_type="general-purpose", run_in_background=true,
  description="Run <exp> on H100",
  prompt="You are an experimenter worker. Follow
    experiments/EXPERIMENTER.md exactly for experiment
    experiments/<exp>/. Start with the dry-run phase; only do the full run
    if the dry-run is green. Report every error to status.md and ALWAYS tear
    the pod down. Repo root: the jarvis checkout you were launched from.")
```
Then poll `experiments/<exp>/status.md`; never block.
