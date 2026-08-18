---
name: runpod-pod-access-from-devbox
description: This dev box can SSH/scp directly into RunPod pods via the runpodctl-managed key
metadata: 
  node_type: memory
  type: reference
  originSessionId: 670f7b65-3fd1-4473-849d-91d4fb505f89
---

The jarvis dev box has a RunPod-account SSH key at
`~/.runpod/ssh/runpodctl-ssh-key` (managed by `runpodctl doctor`, `in_account`),
and RunPod injects that key into every pod's `authorized_keys`. So you can SSH/scp
**directly into any provisioned pod from this box** — no need to sync the user's
laptop credentials:

    runpodctl ssh info <podId>            # prints ip + mapped ssh port
    ssh -i ~/.runpod/ssh/runpodctl-ssh-key -p <port> root@<ip>

**Why this matters:** the RunPod MCP `create-pod` tool has NO startup-command, NO
exec/log, and NO network-volume-attach field. So you provision via MCP but drive
in-pod bringup (install, launch, debug) over this SSH path yourself.

Gotchas learned (2026-06-16, [[open-tinker-infra]]):
- Detached launches over SSH: `setsid`/`nohup` did NOT survive the session — use
  `tmux new-session -d -s <name> "<cmd> > log 2>&1"` (bulletproof).
- Pod image Python is PEP-668 externally-managed → `pip install --break-system-packages`
  (keeps the image's torch; venvs shadow it).
- The RunPod HTTP proxy (`https://<podId>-<port>.proxy.runpod.net`) times out
  long requests (e.g. a ~60s 27B model load) → tunnel instead:
  `ssh ... -N -L <local>:localhost:<port> root@<ip>`.
- Killing a CUDA process with SIGTERM can leak VRAM; check
  `nvidia-smi --query-compute-apps` and `kill -9` stragglers before relaunch.
