# Modal backend

Run `open-tinker-server` on Modal: a warm-GPU control plane + an **autoscaling**
sampler tier. Same wire protocol, same client — only `OPEN_TINKER_BASE_URL` changes.
The Modal sibling of [`../runpod`](../runpod), leaning on Modal's horizontal scale
(https://modal.com/docs/guide/scale).

## Topology

| Tier | Modal primitive | Scales |
|---|---|---|
| Control plane + LoRA training | `@modal.asgi_app()` function | `min=max=1` warm (stateful, sticky by `model_id`) |
| Sampler | `SamplerService` (`@app.cls` + `@modal.concurrent`) | `0..MAX_SAMPLERS` autoscale, scale-to-zero |
| Blob store | Modal Volume `open-tinker-blobs` | shared; commit-after-save / reload-before-load |

The control plane uses a deploy-layer `ModalSampler` (conforms to the server's `Sampler`
protocol) that dispatches each request to `SamplerService`; Modal autoscales it under
concurrent load. The server's RunPod `RemoteVLLMSampler` is untouched. A Modal-Volume
`BlobStore` is injected via `create_app(store=...)` so saved adapters publish to the
shared Volume.

## Prereqs
- `modal token` configured (profile `arcadia-alignment`).
- `huggingface` Modal secret (gated models). Volumes `open-tinker-blobs` /
  `open-tinker-hf-cache` are created on first deploy.

## Runbook (from the repo root)

```bash
# cheap smoke: a small public model on cheap GPUs
export OPEN_TINKER_BASE_MODEL=Qwen/Qwen2.5-0.5B-Instruct
export OPEN_TINKER_MODAL_GPU=L4 OPEN_TINKER_MODAL_SAMPLER_GPU=L4

# 1. PROVISION the base model into the shared HF-cache Volume (separate from serving).
#    Idempotent — re-running is a no-op for an already-cached model.
modal run open-tinker/deploy/modal/app.py::provision
# 2. deploy (the control-plane container mounts the now-populated cache)
modal deploy open-tinker/deploy/modal/app.py
```

**Step 1 is a required, intentional step — not an optional warm-up.** Model
*downloading* is its own provisioning step, deliberately decoupled from serving:
`create_session` loads the base model *inside* the asgi HTTP request, and a cold
download (minutes — ≈4m42s for Qwen2.5-0.5B) exceeds Modal's web-endpoint request
timeout → `500 "lost track of input"` (same class as the RunPod proxy timing out
the model load). Provisioning up front makes the serving-time load a ~seconds cache
read. Add more base models to the same Volume any time — the step is idempotent and
re-runnable:

```bash
modal run open-tinker/deploy/modal/app.py::provision --models Qwen/Qwen2.5-0.5B-Instruct,Qwen/Qwen2.5-1.5B-Instruct
```

Deploy prints the control-plane web URL. Then, unchanged (from `open-tinker/`):

```bash
export OPEN_TINKER_BASE_URL=<control-plane-url>
python deploy/parity_probe.py ours logprobs           # sampling via the autoscaling tier
python deploy/parity_probe.py ours fb                 # training tier
```

## Demonstrate fan-out / autoscale
Prefer a concurrent burst at the deployed `/v1/logprobs` (the control plane fans out to
`SamplerService`; with `OPEN_TINKER_MODAL_MIN_SAMPLERS>0` to avoid cold-start 408s).
`modal run …::fanout` shows `.starmap` but runs an ephemeral app whose image can differ.

## Notes
- Sampler engine is `HFSampler` (no vLLM) for a light image / cheap smoke; swap to
  `LocalVLLMSampler` + a vLLM image for throughput.
- The control plane holds the training session in memory → pinned to one warm container;
  `modal app stop open-tinker` between campaigns to avoid idle GPU cost.
