# RunPod provisioning (task #6)

Ready-to-launch artifacts. **Nothing here spins up paid GPUs automatically** —
the launch steps are explicit and cost money, so run them when you mean to.

## Topology (spec §4)

| Component | RunPod resource | GPU | Scales | Image |
|---|---|---|---|---|
| Control plane + training daemon | **Pod** (persistent) | 1× H100 80GB | manual stop/start | `Dockerfile.training-pod` |
| Sampling workers | **Serverless endpoint** | 1× 80GB | 0..N autoscale | `Dockerfile.sampler-worker` |
| Blob store | **Network Volume** | — | — | mounted at `/mnt/volume` (pod) / `/runpod-volume` (serverless) |

For M1 the training pod also runs an in-process vLLM sampler (`LocalVLLMSampler`),
so the serverless endpoint is optional until rollouts/eval volume justifies it.
Flip to the serverless sampler later with no client change.

## Launch order

1. **Network Volume** — create once; both the pod and the serverless workers
   mount it. (`mcp__runpod__create-network-volume`, or the RunPod console.)
2. **Build + push images** — `deploy/Dockerfile.training-pod` and
   `Dockerfile.sampler-worker` to a registry RunPod can pull
   (`mcp__runpod__create-container-registry-auth` for private registries).
3. **Training pod** — create from the training image, attach the volume at
   `/mnt/volume`, expose `8200` (`mcp__runpod__create-pod`). It serves the
   control plane; point clients at `http://<pod-ip>:8200`.
4. **(Optional) Serverless sampler** — create a template + endpoint from the
   sampler image, attach the volume (`mcp__runpod__create-template`,
   `mcp__runpod__create-endpoint`).

## Client config

```
export OPEN_TINKER_BASE_URL=http://<pod-ip>:8200     # or a tunnel/ingress
export OPEN_TINKER_API_KEY=<shared-token>            # if auth enabled
```
Then `battery-sft` / `battery-distill` work unchanged once the cookbook is told
to `open_tinker.use_as_tinker()` (see `open-tinker/README.md`). A one-line sitecustomize
or a thin wrapper entrypoint can call `use_as_tinker()` before the cookbook imports.

## Cost notes (spec §9)

- Training pod idle cost is the price of statefulness — **stop it between
  campaigns**; the control plane can cold-start it on first
  `create_lora_training_client` (wire this into the pod lifecycle later).
- Serverless scales to zero — you pay per rollout/eval burst.
- 235B is a stretch goal: multi-GPU pod + tensor-parallel vLLM; revisit after M2.

## Not yet automated (intentionally)

Cold-start-on-demand of the training pod, checkpoint TTL GC sweep, and the
control-plane/training split into separate processes are M3 hardening (spec §6).
