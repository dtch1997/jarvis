"""Control plane — FastAPI app implementing the open-tinker wire protocol.

Routes the wire endpoints (WIRE_PROTOCOL.md) to a registry of ``Trainer``
sessions (sticky by ``model_id``) and a ``Sampler``. For M1 the control plane and
the training engine run in ONE process on the persistent pod (simplest
deployable that matches the architecture); the sampler is a pluggable backend
that points at the serverless workers in production. The split into a separate
always-on control plane is a later refactor — the HTTP surface here doesn't
change when that happens.

The engine backends are injected via a ``TrainerFactory`` / ``Sampler`` so the
same app serves the CPU ``Fake*`` backends (tests) and the GPU ``LoRATrainer`` +
vLLM sampler (pod). Request bodies are decoded with the SAME
``open_tinker._serialize`` codecs the client encodes with — one source of truth.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from fastapi import FastAPI, HTTPException, Request

from open_tinker._serialize import decode_datum, encode_tensor  # noqa: F401  (encode_tensor re-exported for backends)

from .blobstore import BlobStore
from .trainers.base import Sampler, Trainer

TrainerFactory = Callable[[str, Dict[str, Any], BlobStore], Trainer]


def create_app(
    trainer_factory: TrainerFactory,
    sampler: Sampler,
    blob_root: str | None = None,
) -> FastAPI:
    app = FastAPI(title="open-tinker control plane", version="0")
    store = BlobStore(blob_root or os.environ.get("OPEN_TINKER_BLOB_ROOT", "/tmp/open-tinker-blobs"))
    sessions: Dict[str, Trainer] = {}
    counter = {"n": 0}

    def _session(model_id: str) -> Trainer:
        if model_id not in sessions:
            raise HTTPException(status_code=404, detail=f"no such session {model_id}")
        return sessions[model_id]

    @app.post("/v1/training/sessions")
    async def create_session(req: Request) -> Dict[str, Any]:
        body = await req.json()
        counter["n"] += 1
        run_id = f"run-{counter['n']:06d}"
        trainer = trainer_factory(run_id, body, store)
        sessions[run_id] = trainer
        return {"model_id": run_id, "base_model": trainer.base_model}

    @app.post("/v1/training/{model_id}/forward_backward")
    async def forward_backward(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        trainer = _session(model_id)
        data = [decode_datum(d) for d in body["data"]]
        return trainer.forward_backward(data, body["loss_fn"], body.get("loss_fn_config"))

    @app.post("/v1/training/{model_id}/optim_step")
    async def optim_step(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        return _session(model_id).optim_step(body["adam_params"])

    @app.post("/v1/training/{model_id}/save")
    async def save(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        path = _session(model_id).save(
            body["kind"], body["name"], body.get("ttl_seconds"), body.get("overwrite", False)
        )
        store.set_ttl(path, body.get("ttl_seconds"))
        return {"path": path}

    @app.post("/v1/training/{model_id}/load_state")
    async def load_state(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        _session(model_id).load_state(body["path"])
        return {"ok": True}

    @app.post("/v1/sample")
    async def sample(req: Request) -> Dict[str, Any]:
        return sampler.sample(await req.json())

    @app.post("/v1/logprobs")
    async def logprobs(req: Request) -> Dict[str, Any]:
        return sampler.compute_logprobs(await req.json())

    @app.get("/v1/capabilities")
    async def capabilities() -> Dict[str, Any]:
        return {
            "models": [os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")],
            "loss_fns": ["cross_entropy", "importance_sampling"],
            "max_lora_rank": 128,
        }

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok", "sessions": str(len(sessions))}

    return app


def main() -> None:
    """Pod entrypoint: serve the real GPU LoRA trainer + (configured) sampler."""
    import uvicorn

    from .trainers.base import Sampler
    from .trainers.lora import make_lora_trainer

    base_model = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
    blob_root = os.environ.get("OPEN_TINKER_BLOB_ROOT")

    # Sampler backend, in preference order:
    #   1. vLLM (perf; serverless workers / GPU-rich pod) if installed
    #   2. HF transformers sampler (lazy load; uses the training pod's own deps)
    # Both load the base model lazily, so server startup stays fast and a
    # training-only run never pays for a sampler it doesn't use.
    sampler: Sampler
    try:
        from .sampler_worker import LocalVLLMSampler

        sampler = LocalVLLMSampler(base_model, blob_root)
    except Exception:  # noqa: BLE001 — vllm absent: use the HF sampler.
        from .hf_sampler import HFSampler

        sampler = HFSampler(base_model, blob_root)

    app = create_app(make_lora_trainer, sampler=sampler, blob_root=blob_root)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8200")))


if __name__ == "__main__":
    main()
