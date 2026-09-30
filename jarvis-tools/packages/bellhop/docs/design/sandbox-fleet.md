# Sandbox fleets

**Status:** v1 (Docker and Modal backends). Direction approved by Daniel on 2026-09-30.

## Why

An RL environment runs the agent's commands in a sandbox. Each rollout gets an isolated
container started from its task's image, and the container is destroyed after grading. A
training run needs dozens to hundreds of sandboxes at once.

Our GPU boxes can't host them:
- A RunPod pod is itself an unprivileged container. It can't start a Docker daemon, and it
  refuses user namespaces, so bubblewrap fails too.
- A Modal GPU sandbox runs under gVisor, and gVisor can't nest Docker.
- The devbox runs Docker, but it has 8 cores and 58 GB of free disk. One agent rollout once
  wrote 60 GB.

So sandboxes run away from the training box, on a backend that every trainer can reach: the
devbox driving Tinker, or a RunPod pod running SkyRL. Sandboxes are CPU work, so they should
not decide where the GPUs come from.

## Boxes and fleets

bellhop's boxes (`pod()`, `sandbox()`, `cluster()`) run *your* code. Each box runs one long
job: you push code, exec it and pull results back.

A fleet runs code you don't trust. It hands out many short-lived sandboxes, one per unit of
work (a rollout or a grading job), and you drive each one command by command. `bellhop.Sandbox`
is the Modal job box. `bellhop.fleet.Sandbox` is the per-rollout protocol described here.

## The contract

```python
from bellhop.fleet import Limits, ModalFleet

async with ModalFleet(run_id="c4", limits=Limits(cpu=2, memory_mb=4096), max_live=64) as fleet:
    sb = await fleet.open(task.image, env={"PIP_NO_INPUT": "1"}, name_hint=task.id)
    res = await sb.exec("pytest -x", workdir="/testbed", timeout=300, max_output_bytes=1_000_000)
    await sb.write_file("/tmp/t.patch", patch)
    text = await sb.read_file("/tmp/out.txt", max_bytes=10_000)
    await sb.close()
```

- **exec.** `exec` runs `timeout T /bin/bash -lc "exec 2>&1 </dev/null; cd <workdir> && <command>"`
  inside the sandbox. This is the convention of Xiaomi's mimoagent backends.
  - Stdout and stderr come back interleaved in `output`.
  - Exit code 124 means the in-sandbox timeout fired, and `timed_out` is then true.
  - The client gives up 30 s after `T`, as a backstop.
  - Output past `max_output_bytes` is dropped while the command keeps draining, and
    `truncated` is then true.
- **SandboxError.** The sandbox itself failed: it is gone, it was killed, or the backend API
  failed. This is never the workload's fault, so callers mask such rollouts instead of scoring
  them.
- **read_file.** It raises `FileNotFoundError` when the file can't be read.
- **Capacity.** `max_live` caps the live sandboxes in a fleet. `open()` waits for a free slot,
  and `close()` is idempotent and frees the slot.
- **Leftovers.** Every sandbox carries its run id as the Docker label or Modal tag
  `bellhop-fleet-run`. Leaving the fleet's `async with` closes its sandboxes and sweeps its run
  id. After a crash, `gc()` or `bellhop fleet gc` do the same.
- **prefetch.** `prefetch(images)` pulls (Docker) or builds (Modal) images ahead of a run, and
  reports the seconds each one took.

## Backends

**DockerFleet** runs containers on the local Docker daemon. It is a port of `agentrl.sandbox`
from science-of-rl-motivations (PR #24), which ran the realistic-rl-pipeline phases B–D.
- **Limits.** `--cpus`, `--memory` (swap set equal), `--pids-limit` and `--init`. The entrypoint
  is an idle `tail -f /dev/null`.
- **Network.** Any Docker network name; the default is `none`.
- **Disk.** Docker on ext4 can't cap a container's writable layer. A disk guard kills any
  sandbox whose writable layer grows past `Limits.disk_gb`, so its next exec raises
  `SandboxError`. A host floor makes `open()` wait while the Docker data disk has less than
  `min_free_gb` free.

**ModalFleet** runs Modal Sandboxes under gVisor. Any machine with a Modal token can reach them.
- **Images.** `modal.Image.from_registry(ref)`. The first use of a ref builds it, which takes
  minutes for a multi-GB image. Later uses start in seconds. The image needs `python` and
  `pip` on PATH, or pass `add_python=`.
- **Limits.** CPU and memory are set as (request, limit) = (limit, limit), which matches
  Docker's hard caps. Modal has no pids or disk knob.
- **Lifetime.** `max_lifetime` (default 2 h) is Modal's server-side timeout, so a leaked
  sandbox dies on its own.
- **Main process.** Each sandbox runs an idle `tail -f /dev/null`, as Docker's does. It never
  runs the image's CMD. Flattened images (`docker import`, like the MiMo task images) have no
  CMD, and Modal then exits the sandbox at once with code 128, so every command fails with
  "Sandbox is shutting down". `python:3.12-slim` hid this, because its CMD (`python3`) waits
  on stdin.
- **Network.** Blocked by default. `outbound_domain_allowlist` and `outbound_cidr_allowlist`
  pass through to Modal.

The two backends differ in these known ways:

| | Docker | Modal |
|---|---|---|
| kernel | the host's (runc) | gVisor, a user-space kernel: slower syscalls, a few unsupported |
| out of memory | the kernel kills a process and the container lives on | the sandbox may die, which raises `SandboxError` |
| disk cap | the guard kills at `Limits.disk_gb` | Modal's own limit |
| network | a Docker network, e.g. an internal one behind a logging proxy | blocked, or allowlists |
| IP for proxy logs | the container's IP on the run's network | none |
| cost | the host | ≈$0.14/core-h + $0.024/GiB-h, 3× Modal functions |

## Not in v1

- **Remote Docker hosts** (`DOCKER_HOST=ssh://…`). The disk floor reads the local disk.
- **Modal's VM runtime**, which runs Docker inside a sandbox for docker-compose tasks. It is in
  alpha and CPU-only; add it when a task needs it.
- GPU sandboxes, snapshots and forking.
- **The logging proxy.** It stays in the env layer. On Modal it needs a new way to tell
  sandboxes apart (see "Open questions").

## Verification

1. **Offline tests** cover argv, create kwargs, error mapping, the output cap, slots and gc.
   They need neither Docker nor the `modal` package.
2. **A live contract suite** runs the same checks on each backend (`BELLHOP_DOCKER_LIVE=1`,
   `MODAL_LIVE=1`).
3. **An env parity check** validates repo_repair's candidate tasks three ways: agentrl's own
   Docker sandbox, `DockerFleet` and `ModalFleet`. Every verdict (rewards, errors, timeouts)
   must match, as the bwrap grader's regrade check did.

## Open questions

- **Image logistics.** The MiMo code images total 6.7 TB, one per task, and Docker Hub
  rate-limits pulls. A large run probably needs a mirror (GCP Artifact Registry) and a
  prefetch pass.
- **Egress on Modal.** Can `outbound_domain_allowlist` pin all traffic to our logging proxy?
  Can the proxy tell sandboxes apart? One way is a per-sandbox credential in `HTTP(S)_PROXY`,
  because Modal gives no stable client IP.
