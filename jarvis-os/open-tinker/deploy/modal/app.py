"""OpenTinker on Modal — warm-GPU control plane + autoscaling sampler tier.

Modal sibling of deploy/runpod, leaning on Modal's horizontal scale
(https://modal.com/docs/guide/scale). The wire-protocol app and the trainer/sampler
engines are unchanged open-tinker-server code; this file is pure infra.

Topology
--------
* **Control plane + LoRA training** — ONE warm GPU container (min=max=1) serving the
  wire protocol via @modal.asgi_app(). Training state (sticky by model_id) lives in
  this container's memory, so it is a single warm container — the RunPod persistent-pod
  model. It forwards sampling to the sampler tier.
* **Sampler tier** — an autoscaling GPU service (`SamplerService`): @modal.concurrent
  for in-container batching + max_containers for horizontal fan-out, scale-to-zero idle.
  This is the Modal analogue of OpenTinker's serverless sampler split (RunPod's is the
  `RemoteVLLMSampler`/`handler` pair in sampler_worker.py — left untouched).
* **Blob store** — a Modal Volume shared by both tiers. The trainer commits after a
  save (via the injected ModalVolumeBlobStore); the sampler reloads before reading.

Deploy:  modal deploy open-tinker/deploy/modal/app.py   (run from the repo, or cd open-tinker)
Client:  set OPEN_TINKER_BASE_URL to the control-plane URL printed on deploy, then use
         open-tinker/deploy/{run_sft,parity_probe}.py unchanged.

Config (env at deploy):
  OPEN_TINKER_BASE_MODEL          base model (default Qwen/Qwen3.6-27B; small for smoke)
  OPEN_TINKER_MODAL_GPU           control-plane GPU (default "H100")
  OPEN_TINKER_MODAL_SAMPLER_GPU   sampler GPU (default = control-plane GPU)
  OPEN_TINKER_MODAL_MAX_SAMPLERS  sampler autoscale ceiling (default 4)
  OPEN_TINKER_MODAL_MIN_SAMPLERS  warm sampler pool (default 0; raise for bursts)
"""

import os
from pathlib import Path

import modal

APP_NAME = "open-tinker"
BLOB_ROOT = "/blobs"
HF_CACHE = "/hf-cache"

BASE_MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
GPU_CONTROL = os.environ.get("OPEN_TINKER_MODAL_GPU", "H100")
GPU_SAMPLER = os.environ.get("OPEN_TINKER_MODAL_SAMPLER_GPU", GPU_CONTROL)
MAX_SAMPLERS = int(os.environ.get("OPEN_TINKER_MODAL_MAX_SAMPLERS", "4"))
MIN_SAMPLERS = int(os.environ.get("OPEN_TINKER_MODAL_MIN_SAMPLERS", "0"))
BLOB_VOLUME = "open-tinker-blobs"
HF_VOLUME = "open-tinker-hf-cache"

# open-tinker/deploy/modal/app.py -> the open-tinker workspace root (holds client/ +
# server/). Only used at deploy time (the add_local_dir build steps); Modal re-imports
# this module in-container as /root/app.py, where the value is unused.
OT_ROOT = Path(__file__).resolve().parent.parent.parent

app = modal.App(APP_NAME)

blob_vol = modal.Volume.from_name(BLOB_VOLUME, create_if_missing=True)
hf_vol = modal.Volume.from_name(HF_VOLUME, create_if_missing=True)
VOLUMES = {BLOB_ROOT: blob_vol, HF_CACHE: hf_vol}
SECRETS = [modal.Secret.from_name("huggingface")]

# Mirrors deploy/runpod/Dockerfile.training-pod via Modal's API. Default torch wheel is
# CUDA-enabled (runs on Modal's injected GPU); transformers/peft cover the LoRA trainer
# ([train]) and the HF sampler. Install client first so server's `open-tinker` dep
# resolves (the uv workspace source isn't honored by plain pip).
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")  # transformers/tinker_cookbook shell out to git
    .pip_install("torch", "transformers", "peft", "accelerate", "hf_transfer")
    .env(
        {
            "OPEN_TINKER_BASE_MODEL": BASE_MODEL,
            "OPEN_TINKER_BLOB_ROOT": BLOB_ROOT,
            "HF_HOME": HF_CACHE,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
    .add_local_dir(str(OT_ROOT / "client"), "/pkg/client", copy=True)
    .add_local_dir(str(OT_ROOT / "server"), "/pkg/server", copy=True)
    .run_commands("pip install /pkg/client", "pip install '/pkg/server[train]'")
)


def _modal_blob_store():
    """A BlobStore whose commit()/reload() publish to / re-sync the shared Volume."""
    from open_tinker_server.blobstore import BlobStore

    class ModalVolumeBlobStore(BlobStore):
        def commit(self) -> None:
            blob_vol.commit()

        def reload(self) -> None:
            blob_vol.reload()

    return ModalVolumeBlobStore(BLOB_ROOT)


# --- Tier 2: autoscaling sampler --------------------------------------------
@app.cls(
    image=image,
    gpu=GPU_SAMPLER,
    volumes=VOLUMES,
    secrets=SECRETS,
    min_containers=MIN_SAMPLERS,  # warm pool (0 = scale-to-zero; raise for bursts)
    max_containers=MAX_SAMPLERS,  # horizontal fan-out ceiling
    scaledown_window=300,
)
@modal.concurrent(max_inputs=4)  # in-container batching of concurrent requests
class SamplerService:
    @modal.enter()
    def _load(self):
        # HF sampler: works on the [train] image with no vLLM. Swap to
        # LocalVLLMSampler (+ a vLLM image) for higher throughput later.
        from open_tinker_server.hf_sampler import HFSampler

        self._sampler = HFSampler(BASE_MODEL, BLOB_ROOT)

    @modal.method()
    def run(self, op: str, req: dict) -> dict:
        if req.get("weights_path"):
            blob_vol.reload()  # pick up an adapter the training tier just committed
        if op == "sample":
            return self._sampler.sample(req)
        if op == "logprobs":
            return self._sampler.compute_logprobs(req)
        raise ValueError(f"unknown op {op!r}")


class ModalSampler:
    """Control-plane Sampler that fans each request to the autoscaling SamplerService.

    Conforms to open_tinker_server's Sampler protocol (sample/compute_logprobs), so it
    drops into create_app(sampler=...) exactly where LocalVLLMSampler / HFSampler /
    RemoteVLLMSampler go. Modal autoscales SamplerService under concurrent load.
    """

    def sample(self, req: dict) -> dict:
        return SamplerService().run.remote("sample", req)

    def compute_logprobs(self, req: dict) -> dict:
        return SamplerService().run.remote("logprobs", req)


# --- Tier 1: control plane + training (one warm GPU container) ---------------
@app.function(
    image=image,
    gpu=GPU_CONTROL,
    volumes=VOLUMES,
    secrets=SECRETS,
    min_containers=1,  # always warm: holds the in-memory training session
    max_containers=1,  # single container: state is sticky by model_id
    scaledown_window=600,
    timeout=3600,
)
@modal.concurrent(max_inputs=8)  # health + wire calls coexist on the one container
@modal.asgi_app()
def control_plane():
    from open_tinker_server.app import create_app
    from open_tinker_server.trainers.lora import make_lora_trainer

    return create_app(
        make_lora_trainer,
        sampler=ModalSampler(),
        store=_modal_blob_store(),
    )


# --- Warm the shared HF cache (run once before serving) ----------------------
@app.function(image=image, volumes=VOLUMES, secrets=SECRETS, timeout=1800)
def warm():
    """Download BASE_MODEL into the shared HF-cache Volume and commit it.

    Run: modal run open-tinker/deploy/modal/app.py::warm   (then (re)deploy)

    Why: create_session loads the base model *inside* the asgi HTTP request; a cold
    download (minutes) exceeds the Modal web-endpoint request timeout → 500. (Same
    class as the RunPod proxy timing out the model load.) Pre-warming the cache so
    the load is seconds keeps create_session within the request budget. Redeploy
    after warming so the warm control-plane container mounts the populated cache.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    AutoTokenizer.from_pretrained(BASE_MODEL)
    AutoModelForCausalLM.from_pretrained(BASE_MODEL)
    hf_vol.commit()
    print(f"warmed HF cache for {BASE_MODEL}")


# --- Batch fan-out demo: Function.map across the autoscaling tier ------------
@app.local_entrypoint()
def fanout(n: int = 16):
    """Fire N logprobs requests across the sampler tier via .starmap (fan-out).

    Run: modal run open-tinker/deploy/modal/app.py::fanout --n 16
    Watch the sampler tier autoscale in `modal app logs open-tinker` / the dashboard.

    NOTE: `modal run` launches an *ephemeral* app whose image is rebuilt and (observed)
    can resolve torch differently from the deployed image. To exercise the real
    autoscaling tier, prefer driving concurrent requests at the *deployed* endpoint's
    /v1/logprobs (a ThreadPoolExecutor burst), which fans out across SamplerService
    containers via the control plane. With min_containers=0 a burst pays cold-start;
    set OPEN_TINKER_MODAL_MIN_SAMPLERS>0.
    """
    prompt = {"tokens": list(range(8))}
    reqs = [("logprobs", {"prompt": prompt, "num_samples": 1}) for _ in range(n)]
    results = list(SamplerService().run.starmap(reqs))
    ok = sum(1 for r in results if isinstance(r, dict) and "logprobs" in r)
    print(f"fanned {n} logprobs across the sampler tier; {ok}/{n} returned logprobs")
