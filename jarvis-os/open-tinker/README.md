# open-tinker — self-hosted Tinker-compatible training infra (RunPod)

Our own training/sampling backend that the existing `battery/train/tinker`
drivers use **unchanged**, to escape the hosted Tinker rate limit.

- **Spec:** [`../docs/specs/runpod-tinker-infra.md`](../docs/specs/runpod-tinker-infra.md)
  — strategy C (scoped SDK clone), hybrid compute, SFT+sampling first milestone.
- **Wire protocol:** [`WIRE_PROTOCOL.md`](WIRE_PROTOCOL.md)

## Workspace layout

Two distributions, deliberately separate so the client's **dependency wall**
(no torch/fastapi) is enforced by packaging, not convention. Client never depends
on server; server depends on client (shared wire codecs + types + protocols).

| Path | Dist | What | Deps |
|---|---|---|---|
| [`client/`](client/) | `open-tinker` | Scoped reimplementation of the `tinker` SDK (`ServiceClient`/`TrainingClient`/`SamplingClient` + types). `use_as_tinker()` shadows `import tinker` so `tinker_cookbook` + battery run unchanged. | numpy, pydantic, httpx (no torch) |
| [`server/`](server/) | `open-tinker-server` | FastAPI control plane + HF/PEFT LoRA trainer + HF/vLLM samplers, implementing the wire protocol. | fastapi; `[train]`→torch/peft; `[sample]`→vllm |
| [`deploy/`](deploy/) | — | Dockerfiles, RunPod provisioning, live-state + parity records, run/probe harnesses. | — |

## How the pieces fit

```
battery-sft / battery-distill
        │  (import tinker  ->  open_tinker.use_as_tinker())
        ▼
tinker_cookbook ──Backend──► control plane (server) ──► LoRA trainer (pod, VRAM-resident)
   HTTPBackend (default)      (wire protocol §5)      └─► HF / vLLM sampler (in-proc / serverless)
   LocalBackend (in-process)                              tinker:// blob store on Network Volume
```

The client talks to the backend through an injectable **`Backend`** seam:
`HTTPBackend` (default, over the wire) or `LocalBackend` (in-process, no socket —
fast tests / single-process runs). See `client/src/open_tinker/protocol.py`.

## Status

**Milestone 1 (SFT + sampling): complete & validated on a live H100.** Real
`battery-sft` on Qwen3.6-27B (nll 1.44→0.26), eval-shim sample + compute_logprobs
from the trained adapter, and numerical parity vs hosted Tinker (loss within 0.17%,
logprobs ~0.01–0.03 nats — `deploy/PARITY_RESULT.md`).

**M2/M3 (stubbed, raise `NotImplementedError`):** `importance_sampling` loss
(on-policy distill) + its parity pass; vLLM serverless deploy + `RemoteVLLMSampler`;
control-plane/trainer split.

## Tests (offline, no GPU)

```
# from this dir (open-tinker/)
PYTHONPATH=client/src:server/src pytest client/tests server/tests
# cookbook import/Config parity (needs the tinker_cookbook venv):
PYTHONPATH=client/src:<repo>/battery/src <cookbook-venv>/bin/python client/tests/parity_cookbook.py
```
