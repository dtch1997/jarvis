# open-tinker-server

Control plane + training/sampling backends implementing the open-tinker wire
protocol (`../WIRE_PROTOCOL.md`) on RunPod. Depends on the `open-tinker` client
(workspace member `../client`) for the shared wire codecs, types, and protocols.

- `app.py` — FastAPI control plane. Routes wire endpoints to a `Trainer` registry
  (sticky by `model_id`) + a `Sampler`. For M1 it runs in one process on the
  training pod; the sampler is pluggable to serverless vLLM workers.
- `trainers/base.py` — re-exports the shared `Trainer` / `Sampler` protocols.
- `trainers/fake.py` — CPU, dependency-free backends for CI/integration tests.
- `trainers/lora.py` — real HF + PEFT LoRA training engine (`[train]` extra).
- `hf_sampler.py` — transformers-based sampler (`[train]` deps; single-pod M1).
- `sampler_worker.py` — vLLM engine + RunPod serverless handler (`[sample]` extra).
- `blobstore.py` — `tinker://` <-> Network Volume path resolver.

## Run (pod)
    pip install -e ../client -e '.[train]'
    OPEN_TINKER_BLOB_ROOT=/mnt/volume OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B \
      open-tinker-server   # serves on :8200

## Test (no GPU)
    # from the open-tinker/ umbrella dir
    PYTHONPATH=client/src:server/src pytest server/tests
