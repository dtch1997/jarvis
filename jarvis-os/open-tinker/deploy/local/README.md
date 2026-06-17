# Local backend

Run `open-tinker-server` on localhost — for development, debugging the wire protocol,
or serving from a single local GPU. No pod, no cloud.

## Install (from the open-tinker workspace root)

```bash
uv sync                                  # workspace: client + server
# or, for the GPU engines:
pip install -e client -e 'server[train]'   # + real LoRA trainer (torch/peft)
pip install -e 'server[sample]'            # + in-process vLLM sampler (GPU)
```

## Run

```bash
export OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B     # or a small model for dev
export OPEN_TINKER_BLOB_ROOT=/tmp/open-tinker-blobs  # local fs blob store
export PORT=8200
open-tinker-server                                  # uvicorn on 0.0.0.0:8200
```

`app.main()` picks the sampler: `RemoteVLLMSampler` if `OPEN_TINKER_SAMPLER_ENDPOINT_ID`
is set, else in-process vLLM (`[sample]`), else the HF sampler (CPU float32 when no
CUDA — fine for small models / smoke). For protocol-only dev without GPU deps, the Fake
backends are exercised by the suite:

```bash
PYTHONPATH=client/src:server/src pytest client/tests server/tests
```

## Point a client at it

```bash
export OPEN_TINKER_BASE_URL=http://localhost:8200
python deploy/parity_probe.py ours          # or deploy/run_sft.py --smoke ...
```
Same harness as every other backend — only the URL changes.
