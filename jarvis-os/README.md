# Self-hosted Tinker-compatible training infra (RunPod)

Our own training/sampling backend that the existing `battery/train/tinker`
drivers use **unchanged**, to escape the hosted Tinker rate limit.

- **Spec:** [`docs/specs/runpod-tinker-infra.md`](docs/specs/runpod-tinker-infra.md)
  — strategy C (scoped SDK clone), hybrid compute, SFT+sampling first milestone.
- **Wire protocol:** [`open-tinker/WIRE_PROTOCOL.md`](open-tinker/WIRE_PROTOCOL.md)

## Packages

| Path | What | Deps |
|---|---|---|
| [`open-tinker/`](open-tinker/) | Client: scoped reimplementation of the `tinker` SDK (`ServiceClient`/`TrainingClient`/`SamplingClient` + types). `use_as_tinker()` shadows `import tinker` so `tinker_cookbook` + battery run unchanged. | numpy, pydantic, httpx (no torch) |
| [`open-tinker-server/`](open-tinker-server/) | Backend: FastAPI control plane + HF/PEFT LoRA trainer + vLLM sampler, implementing the wire protocol. | fastapi; `[train]`→torch/peft; `[sample]`→vllm |
| [`deploy/`](deploy/) | Dockerfiles + RunPod provisioning guide. | — |

## How the pieces fit

```
battery-sft / battery-distill
        │  (import tinker  ->  open_tinker.use_as_tinker())
        ▼
tinker_cookbook ──HTTP──► open-tinker-server control plane ──► LoRA trainer (pod, VRAM-resident)
                          (wire protocol §5)                └─► vLLM sampler (in-proc M1 / serverless)
                                                                tinker:// blob store on Network Volume
```

## Status (milestone 1: SFT + sampling)

| # | Task | State |
|---|---|---|
| 1 | Scoped SDK clone scaffold | ✅ done |
| 2 | Cookbook import + Config parity | ✅ done (7/7) |
| 3 | Wire protocol + serialization | ✅ done |
| 4 | Control plane | ✅ done (HTTP-tested) |
| 5 | LoRA training engine | ◐ code done + CPU core-math validated; GPU run pending |
| 6 | RunPod provisioning | ◐ artifacts ready; launch pending (spends $) |
| 7 | vLLM sampler | ◐ code done; GPU run pending |
| 8 | Numerical parity vs real Tinker | ☐ needs live infra + Tinker |
| 9 | End-to-end `battery-sft` + eval | ☐ needs live infra |

**Tests (all offline, no GPU): 23 green** + 7/7 cookbook parity.

```
PYTHONPATH=open-tinker/src:open-tinker-server/src pytest open-tinker/tests open-tinker-server/tests
# cookbook parity (needs the tinker_cookbook venv):
PYTHONPATH=open-tinker/src:<repo>/battery/src <cookbook-venv>/bin/python open-tinker/tests/parity_cookbook.py
```
