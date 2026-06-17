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

## Demonstrate fan-out / autoscale + right-size the warm pool
Drive a concurrent burst at the **deployed** `/v1/logprobs` — the control plane fans it
out across `SamplerService` containers, so you exercise the tier you actually serve
(`modal run …::fanout` ran an *ephemeral* app whose rebuilt image can resolve torch
differently). `deploy/fanout_demo.py` fires the burst and prints the latency
distribution:

```bash
export OPEN_TINKER_BASE_URL=<control-plane-url>
python deploy/fanout_demo.py --n 32 --concurrency 16
```

**Right-sizing `OPEN_TINKER_MODAL_MIN_SAMPLERS`:** warm samplers return in ~the model's
forward time; a burst wider than the warm pool spills onto cold containers that pay the
full model load (long p95/max tail, and 408/5xx past the request timeout). Raise
MIN_SAMPLERS toward your expected burst concurrency until the tail collapses, then stop —
warm GPUs are idle $. `MAX_SAMPLERS` still absorbs spikes above the warm pool (at
cold-start latency).

## Large models (>1 GPU): multi-GPU sharding

A base model that doesn't fit one GPU (e.g. >100B) is sharded across the GPUs of the
**single** control-plane container — accelerate `device_map` naive pipeline parallelism;
PEFT trains the LoRA adapter on top unchanged. The decision lives server-side in
`server/.../device_map.py` (auto-shards once it sees >1 GPU).

```bash
# 8×H100 in one container; provision the big base, then deploy.
export OPEN_TINKER_BASE_MODEL=<a >100B repo>
export OPEN_TINKER_MODAL_GPU=H100:8 OPEN_TINKER_MODAL_SAMPLER_GPU=H100:8
modal run open-tinker/deploy/modal/app.py::provision      # ~200GB+ download, once
modal deploy open-tinker/deploy/modal/app.py
```

- The control plane stays `min=max=1` (sticky training state) — sharding adds GPUs to
  that one container, it does **not** add containers.
- `OPEN_TINKER_DEVICE_MAP` overrides the policy (`auto` | `balanced` | `sequential` | a
  JSON map | `single` to force one GPU); `OPEN_TINKER_MAX_MEMORY` (JSON, e.g.
  `{"0":"70GiB","1":"70GiB"}`) caps per-GPU usage to leave headroom for activations +
  optimizer state, or to force a split in a smoke test.
- Gradient checkpointing is auto-enabled on the sharded path (the frozen base fills most
  of each GPU, so retained activations — worst on shard 0 — are what OOMs the backward).
- Throughput note: `device_map` is naive pipeline (one shard active at a time) — fine for
  a stress test / correctness, not optimal MFU. Tensor-parallel vLLM (sampler, #31) and
  FSDP/ZeRO sharded *training* are the perf follow-ups.

### Validated: Qwen3-235B-A22B (MoE) on 8×H100
Smoke via the `stress_test` entrypoint (drives the sharded `LoRATrainer` directly — a
>100B base takes minutes to load into VRAM, which would blow the asgi *request* timeout
inside `create_session`; serving >100B over HTTP needs load-at-startup, a separate step):

```bash
export OPEN_TINKER_MODAL_GPU=H100:8 OPEN_TINKER_DEVICE_MAP=auto
# device_map="auto" overloads shard 0 (embeddings + most layers + I/O activations); cap it
# lower so the backward has headroom. expandable_segments avoids fragmentation OOMs.
export OPEN_TINKER_MAX_MEMORY='{"0":"54GiB","1":"68GiB","2":"68GiB","3":"68GiB","4":"68GiB","5":"68GiB","6":"68GiB","7":"68GiB"}'
modal run open-tinker/deploy/modal/app.py::provision --models Qwen/Qwen3-235B-A22B-Instruct-2507  # 470GB, ~27min
modal run open-tinker/deploy/modal/app.py::stress_test --model Qwen/Qwen3-235B-A22B-Instruct-2507
```
Result: 470GB sharded across all 8 H100s, LoRA trained, loss `1.85 → 0.58` over 6 steps
(~65s/step, naive pipeline). Provision (470GB) took 26m47s.

## Notes
- Sampler engine is `HFSampler` (no vLLM) for a light image / cheap smoke; swap to
  `LocalVLLMSampler` + a vLLM image for throughput.
- The control plane holds the training session in memory → pinned to one warm container;
  `modal app stop open-tinker` between campaigns to avoid idle GPU cost.
