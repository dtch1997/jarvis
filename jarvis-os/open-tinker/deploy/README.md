# Deploying open-tinker-server

`open-tinker-server` is one portable FastAPI app (the wire protocol). **Where** it runs
is an infra choice; the `open-tinker` client is URL-agnostic — it only needs
`OPEN_TINKER_BASE_URL`. One subdirectory per backend, plus a shared, backend-agnostic
verification harness.

## Backends

| Dir | What it is | When |
|---|---|---|
| [`local/`](local/) | Run the server on localhost (uvicorn; HFSampler or CPU fake) | dev / debugging / a single local GPU |
| [`runpod/`](runpod/) | Persistent H100 pod + (optional) serverless sampler + Network Volume | the parity-validated GPU deployment |
| [`modal/`](modal/) | Warm GPU control plane + **autoscaling** sampler tier on Modal | scale-out sampling, scale-to-zero |

The trainer/sampler backends are injected via `open_tinker_server.app.create_app(...)`,
so the infra choice never touches the client or the wire protocol.

## Shared verification harness (works against any backend's URL)

- `run_sft.py` — runs `aligne-sft` against the backend via `open_tinker.use_as_tinker()`
  (battery runs unchanged, only the tinker backend is swapped).
- `parity_probe.py` — deterministic single-step probe (base-model `compute_logprobs`;
  `forward_backward` with a fresh LoRA) emitting JSON, so `ours` vs hosted `tinker`
  can be diffed. Model from `OPEN_TINKER_BASE_MODEL`.

```
OPEN_TINKER_BASE_URL=<url> python deploy/parity_probe.py ours logprobs   # or: tinker
OPEN_TINKER_BASE_URL=<url> python deploy/run_sft.py --smoke --data conversations.jsonl --model <m>
```
Point `OPEN_TINKER_BASE_URL` at whichever backend you launched; the harness is identical.
