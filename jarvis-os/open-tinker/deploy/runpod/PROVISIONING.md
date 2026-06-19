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
**M3 hybrid split:** set `OPEN_TINKER_SAMPLER_ENDPOINT_ID=<endpoint-id>` on the
control-plane process and it uses `RemoteVLLMSampler` instead — forwarding
`sample`/`compute_logprobs` to the serverless endpoint's `runsync` route (auth via
`RUNPOD_API_KEY`). The control plane then holds no model, so it can run on a cheap
CPU box while the GPU samplers autoscale to zero. No client change either way.

## Launch order

1. **Network Volume** — create once; both the pod and the serverless workers
   mount it. (`mcp__runpod__create-network-volume`, or the RunPod console.)
2. **Build + push images** — `deploy/runpod/Dockerfile.training-pod` and
   `Dockerfile.sampler-worker` to a registry RunPod can pull
   (`mcp__runpod__create-container-registry-auth` for private registries).
3. **Training pod** — create from the training image, attach the volume at
   `/mnt/volume`, expose `8200` (`mcp__runpod__create-pod`). It serves the
   control plane; point clients at `http://<pod-ip>:8200`.
4. **(Optional) Serverless sampler** — create a template + endpoint from the
   sampler image, attach the volume (`mcp__runpod__create-template`,
   `mcp__runpod__create-endpoint`). For the hybrid split, set
   `OPEN_TINKER_SAMPLER_ENDPOINT_ID=<endpoint-id>` (+ `RUNPOD_API_KEY`) on the
   control-plane process so it routes sampling there.

## Client config

```
export OPEN_TINKER_BASE_URL=http://<pod-ip>:8200     # or a tunnel/ingress
export OPEN_TINKER_API_KEY=<shared-token>            # if auth enabled
```
Then `aligne-sft` / `aligne-distill` work unchanged once the cookbook is told
to `open_tinker.use_as_tinker()` (see `open-tinker/README.md`). A one-line sitecustomize
or a thin wrapper entrypoint can call `use_as_tinker()` before the cookbook imports.

## Cost notes (spec §9)

- Training pod idle cost is the price of statefulness — **stop it between
  campaigns**; the control plane can cold-start it on first
  `create_lora_training_client` (wire this into the pod lifecycle later).
- Serverless scales to zero — you pay per rollout/eval burst.
- 235B is a stretch goal: multi-GPU pod + tensor-parallel vLLM; revisit after M2.

## M3 hardening (implemented)

- **Hybrid split** — `RemoteVLLMSampler` + `OPEN_TINKER_SAMPLER_ENDPOINT_ID`
  (above): the control plane forwards sampling to the serverless endpoint, so it
  no longer needs a GPU. Run it on a cheap CPU pod separate from the training pod.
- **Checkpoint TTL GC** — `BlobStore.gc()` removes checkpoints whose
  `save_state(ttl_seconds=...)` has elapsed. Call it on a schedule (cron / a
  periodic task on the control plane) to keep the Network Volume from filling.
- **Idempotency** — the control plane dedups/orders per-`model_id` `seq_id`
  (replay retries, 409 on stale), so client retries are safe.

## Not yet automated (intentionally)

Cold-start-on-demand of the training pod, and a scheduled trigger for the
`BlobStore.gc()` sweep (the sweep itself exists; wiring it to cron is a deploy
choice). Multi-run scheduling on one pod and wandb passthrough remain future work.
