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

Provision (once per base model, before deploy):
         modal run open-tinker/deploy/modal/app.py::provision
         Downloads weights into the shared HF-cache Volume so serving-time loads are
         a ~seconds cache read instead of a multi-minute download inside the request.
Deploy:  modal deploy open-tinker/deploy/modal/app.py   (run from the repo, or cd open-tinker)
Client:  set OPEN_TINKER_BASE_URL to the control-plane URL printed on deploy, then use
         open-tinker/deploy/{run_sft,parity_probe}.py unchanged.

Config (env at deploy):
  OPEN_TINKER_BASE_MODEL          base model (default Qwen/Qwen3.6-27B; small for smoke)
  OPEN_TINKER_MODAL_GPU           control-plane GPU (default "H100"); "H100:8" for a
                                  multi-GPU container that can shard a >100B base model
  OPEN_TINKER_MODAL_SAMPLER_GPU   sampler GPU (default = control-plane GPU)
  OPEN_TINKER_MODAL_MAX_SAMPLERS  sampler autoscale ceiling (default 4)
  OPEN_TINKER_MODAL_MIN_SAMPLERS  warm sampler pool (default 0; raise for bursts)
  OPEN_TINKER_SAMPLER_BACKEND     "hf" (default) or "vllm". "vllm" runs the sampler
                                  tier on a vLLM image (LocalVLLMSampler) for
                                  throughput; "hf" reuses the [train] image (no extra
                                  build). The control plane / trainer are unchanged.
  OPEN_TINKER_MAX_LORA_RANK       vLLM LoRA rank cap (default 128 = advertised max;
                                  must cover the trainer's adapter rank, default 32)
  OPEN_TINKER_DEVICE_MAP          shard a too-big-for-one-GPU base across the container's
                                  GPUs (unset => auto when >1 GPU; see server/device_map.py)
  OPEN_TINKER_MAX_MEMORY          per-device memory cap, JSON (leaves headroom / forces a split)
"""

import os
from pathlib import Path

import modal

APP_NAME = "open-tinker"
BLOB_ROOT = "/blobs"
HF_CACHE = "/hf-cache"

BASE_MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
# Multi-GPU: request several GPUs per container with the Modal "TYPE:count" form
# (e.g. OPEN_TINKER_MODAL_GPU=H100:8). The control plane stays ONE container (sticky
# state); the extra GPUs let the server shard a >1-GPU base model across them via
# OPEN_TINKER_DEVICE_MAP (server/device_map.py). Default "auto" sharding kicks in
# automatically once >1 GPU is visible.
GPU_CONTROL = os.environ.get("OPEN_TINKER_MODAL_GPU", "H100")
GPU_SAMPLER = os.environ.get("OPEN_TINKER_MODAL_SAMPLER_GPU", GPU_CONTROL)
# Sharding knobs forwarded into the container (see server/device_map.py). Unset =>
# auto-shard iff >1 GPU. OPEN_TINKER_MAX_MEMORY caps per-device usage (JSON).
DEVICE_MAP = os.environ.get("OPEN_TINKER_DEVICE_MAP")
MAX_MEMORY = os.environ.get("OPEN_TINKER_MAX_MEMORY")
MAX_SAMPLERS = int(os.environ.get("OPEN_TINKER_MODAL_MAX_SAMPLERS", "4"))
MIN_SAMPLERS = int(os.environ.get("OPEN_TINKER_MODAL_MIN_SAMPLERS", "0"))
# Sampler engine: "hf" (HFSampler on the [train] image, current default — no extra
# build, the #21-validated path) or "vllm" (LocalVLLMSampler on a vLLM image, for
# throughput). Read at deploy/import time so it selects both the image and the
# in-container engine; the control plane + trainer are unaffected either way.
SAMPLER_BACKEND = os.environ.get("OPEN_TINKER_SAMPLER_BACKEND", "hf").strip().lower()
if SAMPLER_BACKEND not in ("hf", "vllm"):
    raise ValueError(
        f"OPEN_TINKER_SAMPLER_BACKEND must be 'hf' or 'vllm', got {SAMPLER_BACKEND!r}"
    )
MAX_LORA_RANK = os.environ.get("OPEN_TINKER_MAX_LORA_RANK")
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

# Env shared by every tier's image (control plane, trainer, sampler). Kept in one
# place so the [train] and vLLM images stay in lockstep on cache/sharding policy.
COMMON_ENV = {
    "OPEN_TINKER_BASE_MODEL": BASE_MODEL,
    "OPEN_TINKER_BLOB_ROOT": BLOB_ROOT,
    "HF_HOME": HF_CACHE,
    # hf-xet high-performance transfer (the modern path; HF_HUB_ENABLE_HF_TRANSFER
    # is deprecated/ignored under hf-xet). Matters most for big-model provisioning
    # — without it Xet runs at conservative concurrency (~300MB/s observed on a
    # 470GB pull) vs the multi-GB/s the network can sustain.
    "HF_XET_HIGH_PERFORMANCE": "1",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",  # harmless fallback for non-Xet hub versions
    # Reduce CUDA fragmentation on a tightly-packed sharded model: with the base
    # filling most of each GPU, the forward/backward's transient buffers must fit
    # in the slack, and PyTorch's default caching allocator fragments it. Lets a
    # >100B sharded model leave room for activations without OOM.
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    # Forward the sharding knobs only when set, so the in-container
    # trainer/sampler see the same policy chosen at deploy time. Unset =>
    # the server auto-shards iff it sees >1 GPU (server/device_map.py).
    **({"OPEN_TINKER_DEVICE_MAP": DEVICE_MAP} if DEVICE_MAP else {}),
    **({"OPEN_TINKER_MAX_MEMORY": MAX_MEMORY} if MAX_MEMORY else {}),
    # vLLM LoRA rank cap; forwarded only when set (the engine defaults to the
    # advertised 128 otherwise). See server/sampler_worker._engine_kwargs_from_env.
    **({"OPEN_TINKER_MAX_LORA_RANK": MAX_LORA_RANK} if MAX_LORA_RANK else {}),
}

# Mirrors deploy/runpod/Dockerfile.training-pod via Modal's API. Default torch wheel is
# CUDA-enabled (runs on Modal's injected GPU); transformers/peft cover the LoRA trainer
# ([train]) and the HF sampler. Install client first so server's `open-tinker` dep
# resolves (the uv workspace source isn't honored by plain pip).
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")  # transformers/tinker_cookbook shell out to git
    .pip_install("torch", "transformers", "peft", "accelerate", "hf_transfer")
    .env(COMMON_ENV)
    .add_local_dir(str(OT_ROOT / "client"), "/pkg/client", copy=True)
    .add_local_dir(str(OT_ROOT / "server"), "/pkg/server", copy=True)
    .run_commands("pip install /pkg/client", "pip install '/pkg/server[train]'")
)

# vLLM sampler image (OPEN_TINKER_SAMPLER_BACKEND=vllm). vLLM pins its own torch +
# transformers, so we DON'T pre-pip torch here — installing the `[sample]` extra
# (vllm) pulls a self-consistent CUDA stack. hf_transfer keeps adapter/cache reads
# fast. Only built/used when the vLLM backend is selected; the [train] image above
# still serves the control plane + trainer tier.
vllm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("hf_transfer")
    .env(COMMON_ENV)
    .add_local_dir(str(OT_ROOT / "client"), "/pkg/client", copy=True)
    .add_local_dir(str(OT_ROOT / "server"), "/pkg/server", copy=True)
    .run_commands("pip install /pkg/client", "pip install '/pkg/server[sample]'")
)

# The sampler tier runs on whichever image the selected backend needs.
sampler_image = vllm_image if SAMPLER_BACKEND == "vllm" else image


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
    image=sampler_image,
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
        # Engine chosen at deploy time by OPEN_TINKER_SAMPLER_BACKEND (must match the
        # image selected above): vLLM for throughput, else the HF sampler (works on
        # the [train] image with no vLLM). Both honor the Sampler protocol, so the
        # ModalSampler fan-out below is identical regardless of backend.
        if SAMPLER_BACKEND == "vllm":
            from open_tinker_server.sampler_worker import LocalVLLMSampler

            self._sampler = LocalVLLMSampler(BASE_MODEL, BLOB_ROOT)
        else:
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


# --- Provision: download base-model weights into the shared HF cache ---------
# A first-class, explicit, idempotent step — NOT a serving-time side effect. Run it
# before (or independently of) deploy; the serving path then assumes weights are
# already cached (load-from-cache is ~seconds and stays inside the create_session
# request budget). Re-runnable to add more base models to the shared Volume.
@app.function(image=image, volumes=VOLUMES, secrets=SECRETS, timeout=5400)
def provision(models: str = BASE_MODEL):
    """Download one or more base models into the shared HF-cache Volume and commit.

    Run:  modal run open-tinker/deploy/modal/app.py::provision               # BASE_MODEL
          modal run open-tinker/deploy/modal/app.py::provision --models A,B  # add more

    `models` is a comma-separated list of HF repo ids (default: the deploy's
    OPEN_TINKER_BASE_MODEL). Idempotent: an already-cached model is detected and
    skipped, so re-running is cheap and safe; re-run with new ids to add base models.

    Why this is a separate step: create_session loads the base model *inside* the
    asgi HTTP request, and a cold download (minutes — e.g. ≈4m42s for Qwen2.5-0.5B)
    exceeds the Modal web-endpoint request timeout → 500 "lost track of input"
    (same class as the RunPod proxy timing out the model load). Provisioning the
    cache up front makes the serving-time load a ~seconds cache read. The
    control-plane container mounts this Volume, so a deploy that follows
    provisioning serves create_session immediately — no manual warm-up.
    """
    from huggingface_hub import snapshot_download

    requested = [m.strip() for m in models.split(",") if m.strip()]
    if not requested:
        raise ValueError("provision: no models requested (empty --models)")

    hf_vol.reload()  # see anything a prior provision committed
    for model in requested:
        try:
            # Cache hit? A local-only fetch succeeds iff every file is already cached.
            snapshot_download(model, local_files_only=True)
            print(f"provision: {model} already cached — skipping")
            continue
        except Exception:  # noqa: BLE001  (not cached / incomplete -> download below)
            pass
        print(f"provision: downloading {model} ...")
        # Download the *files* only — do NOT instantiate (AutoModel...from_pretrained
        # would pull the whole model into this CPU container's RAM and OOM on a >100B
        # model). snapshot_download streams the safetensors straight to the cache.
        # max_workers raises file-level concurrency (default 8); combined with
        # HF_XET_HIGH_PERFORMANCE (image env) this saturates the link on a >100B pull.
        snapshot_download(model, max_workers=16)
        print(f"provision: cached {model}")

    hf_vol.commit()
    print(f"provision: HF cache committed for {len(requested)} model(s): {requested}")


# --- >100B sharded-training smoke -------------------------------------------
@app.function(image=image, gpu=GPU_CONTROL, volumes=VOLUMES, secrets=SECRETS, timeout=5400)
def stress_test(model: str = BASE_MODEL, steps: int = 5, rank: int = 8):
    """Load a >100B model sharded across the container's GPUs and train a few steps.

    Run (provision the weights first):
      OPEN_TINKER_MODAL_GPU=H100:8 OPEN_TINKER_DEVICE_MAP=auto \\
        modal run open-tinker/deploy/modal/app.py::stress_test \\
        --model Qwen/Qwen3-235B-A22B-Instruct-2507

    Drives the sharded ``LoRATrainer`` DIRECTLY (no asgi) on purpose: loading ~470GB
    into VRAM takes minutes, which would blow the web-endpoint *request* timeout if it
    happened inside ``create_session`` (the provision step only moved the *download*
    out, not the load). Serving a >100B model over HTTP needs the base loaded at
    container startup — a separate productionization step. This smoke isolates the
    thing we're validating: that sharded LoRA *training* of a >100B model runs and the
    loss moves.
    """
    import time

    import torch
    from transformers import AutoTokenizer

    from open_tinker.types import Datum, ModelInput, TensorData
    from open_tinker_server.trainers.lora import LoRATrainer

    hf_vol.reload()
    print(f"stress_test: {torch.cuda.device_count()} GPU(s) visible; loading {model} ...")
    t0 = time.time()
    tr = LoRATrainer("run-stress", {"base_model": model, "lora": {"rank": rank}}, _modal_blob_store())
    print(f"stress_test: sharded trainer built in {time.time() - t0:.0f}s")

    tok = AutoTokenizer.from_pretrained(model)
    ids = tok.encode("The capital of France is Paris, a city known for its art and history.")
    datum = Datum(
        model_input=ModelInput.from_ints(ids[:-1]),
        loss_fn_inputs={
            "target_tokens": TensorData.from_torch(torch.tensor(ids[1:])),
            "weights": TensorData.from_torch(torch.ones(len(ids) - 1)),
        },
    )

    losses = []
    for i in range(steps):
        t = time.time()
        out = tr.forward_backward([datum], "cross_entropy", None)
        tr.optim_step({"learning_rate": 1e-4})
        loss = out["metrics"]["loss:mean"]
        losses.append(loss)
        print(f"stress_test: step {i} loss={loss:.4f} ({time.time() - t:.0f}s)")

    print(f"stress_test: loss {losses[0]:.4f} -> {losses[-1]:.4f} over {steps} steps")
    ok = losses[-1] < losses[0]
    print(f"stress_test: {'PASS' if ok else 'FAIL'} — >100B sharded LoRA training "
          f"{'trains (loss decreased)' if ok else 'did NOT reduce loss'}")
    return {"model": model, "losses": losses, "ok": ok}


# --- Batch fan-out / autoscale demo -----------------------------------------
# Drive the *deployed* endpoint, not an ephemeral `modal run` app: a concurrent
# burst at /v1/logprobs fans out across SamplerService via the control plane and
# exercises the tier you actually serve (the old `::fanout` ::starmap entrypoint
# ran an ephemeral app whose rebuilt image could resolve torch differently). See
# deploy/fanout_demo.py — it also reports the latency tail used to right-size
# OPEN_TINKER_MODAL_MIN_SAMPLERS:
#     export OPEN_TINKER_BASE_URL=<control-plane-url>   # printed on deploy
#     python deploy/fanout_demo.py --n 32 --concurrency 16
