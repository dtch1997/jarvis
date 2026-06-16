# open-tinker-server

Control plane + training/sampling backends implementing the open-tinker wire
protocol (`open-tinker/WIRE_PROTOCOL.md`) on RunPod.

- `app.py` — FastAPI control plane. Routes wire endpoints to a `Trainer` registry
  (sticky by `model_id`) + a `Sampler`. For M1 it runs in one process on the
  training pod; the sampler points at serverless vLLM workers.
- `trainers/base.py` — `Trainer` / `Sampler` interfaces.
- `trainers/fake.py` — CPU, dependency-free backends for CI/integration tests.
- `trainers/lora.py` — real HF + PEFT LoRA training engine (`[train]` extra) and
  the vLLM sampler stub (`[sample]` extra, task #7).
- `blobstore.py` — `tinker://` <-> Network Volume path resolver.

## Run (pod)
    pip install -e 'open-tinker-server[train]'
    OPEN_TINKER_BLOB_ROOT=/mnt/volume OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B \
      open-tinker-server   # serves on :8200

## Test (no GPU)
    PYTHONPATH=open-tinker/src:open-tinker-server/src pytest open-tinker-server/tests
