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
import time
from collections import OrderedDict
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
    store: BlobStore | None = None,
) -> FastAPI:
    app = FastAPI(title="open-tinker control plane", version="0")
    # A deployment may inject a backend-specific store (e.g. a Modal-Volume store
    # whose commit()/reload() publish to a separate sampler tier); else a plain
    # filesystem store under blob_root.
    store = store or BlobStore(
        blob_root or os.environ.get("OPEN_TINKER_BLOB_ROOT", "/tmp/open-tinker-blobs")
    )
    # Each session is a ``LoRATrainer`` holding a full base model + LoRA adapter +
    # AdamW state in VRAM. Without eviction the dict grows one resident model per
    # ``create_session`` and a long-lived control plane OOMs. Bound it three ways:
    # an LRU capacity cap (OPEN_TINKER_MAX_SESSIONS, evict least-recently-used on
    # overflow), an idle TTL (OPEN_TINKER_SESSION_TTL_SECONDS, swept lazily on
    # access), and an explicit DELETE. Eviction calls the trainer's optional
    # ``close()`` to drop model refs + free CUDA memory. OrderedDict tracks LRU
    # order; we move_to_end on every touch. <=0 capacity / TTL means "unbounded".
    max_sessions = int(os.environ.get("OPEN_TINKER_MAX_SESSIONS", "8"))
    session_ttl = float(os.environ.get("OPEN_TINKER_SESSION_TTL_SECONDS", "0") or 0)
    sessions: "OrderedDict[str, Trainer]" = OrderedDict()
    last_access: Dict[str, float] = {}
    counter = {"n": 0}
    # Per-model_id idempotency (WIRE_PROTOCOL.md "Ordering & idempotency"): the
    # client submits FIFO with a monotonic seq_id, so a re-sent seq_id is a retry
    # (replay the cached response — re-running forward_backward would DOUBLE the
    # accumulated gradient), and a seq_id below the last one is stale → 409. We
    # cache only the most recent response per model_id, which covers the realistic
    # retry (the request whose response was lost in flight).
    seq_state: Dict[str, Dict[str, Any]] = {}

    def _evict(model_id: str) -> None:
        """Drop a session and reclaim its VRAM (via the trainer's optional close())."""
        trainer = sessions.pop(model_id, None)
        last_access.pop(model_id, None)
        seq_state.pop(model_id, None)  # idempotency cache is per-session — drop with it
        close = getattr(trainer, "close", None)
        if callable(close):
            close()

    def _sweep_expired() -> None:
        if not session_ttl:
            return
        now = time.monotonic()
        for mid in [m for m, t in last_access.items() if now - t > session_ttl]:
            _evict(mid)

    def _session(model_id: str) -> Trainer:
        _sweep_expired()
        if model_id not in sessions:
            raise HTTPException(status_code=404, detail=f"no such session {model_id}")
        sessions.move_to_end(model_id)  # touch → most-recently-used
        last_access[model_id] = time.monotonic()
        return sessions[model_id]

    def _with_seq(model_id: str, body: Dict[str, Any], compute):
        """Apply seq_id dedup/ordering around a mutating per-session op."""
        seq_id = body.get("seq_id")
        if seq_id is None:  # no seq_id (e.g. a direct/test caller): just run it.
            return compute()
        st = seq_state.get(model_id)
        if st is not None:
            if seq_id == st["last"]:
                return st["response"]  # idempotent replay of the last op
            if seq_id < st["last"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"stale seq_id {seq_id} (last={st['last']}) for {model_id}",
                )
        resp = compute()
        seq_state[model_id] = {"last": seq_id, "response": resp}
        return resp

    @app.post("/v1/training/sessions")
    async def create_session(req: Request) -> Dict[str, Any]:
        body = await req.json()
        _sweep_expired()
        # Evict LRU down to capacity-1 BEFORE building the new trainer, so loading
        # the new model doesn't transiently push VRAM to max+1.
        while max_sessions > 0 and len(sessions) >= max_sessions:
            _evict(next(iter(sessions)))  # next(iter(...)) == least-recently-used
        counter["n"] += 1
        run_id = f"run-{counter['n']:06d}"
        trainer = trainer_factory(run_id, body, store)
        sessions[run_id] = trainer
        last_access[run_id] = time.monotonic()
        return {"model_id": run_id, "base_model": trainer.base_model}

    @app.delete("/v1/training/{model_id}")
    async def close_session(model_id: str) -> Dict[str, Any]:
        if model_id not in sessions:
            raise HTTPException(status_code=404, detail=f"no such session {model_id}")
        _evict(model_id)
        return {"ok": True}

    @app.post("/v1/training/{model_id}/forward_backward")
    async def forward_backward(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        trainer = _session(model_id)

        def _run():
            data = [decode_datum(d) for d in body["data"]]
            return trainer.forward_backward(data, body["loss_fn"], body.get("loss_fn_config"))

        return _with_seq(model_id, body, _run)

    @app.post("/v1/training/{model_id}/optim_step")
    async def optim_step(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        trainer = _session(model_id)
        return _with_seq(model_id, body, lambda: trainer.optim_step(body["adam_params"]))

    @app.post("/v1/training/{model_id}/save")
    async def save(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        trainer = _session(model_id)

        def _run():
            path = trainer.save(
                body["kind"], body["name"], body.get("ttl_seconds"), body.get("overwrite", False)
            )
            store.set_ttl(path, body.get("ttl_seconds"))
            return {"path": path}

        return _with_seq(model_id, body, _run)

    @app.post("/v1/training/{model_id}/load_state")
    async def load_state(model_id: str, req: Request) -> Dict[str, Any]:
        body = await req.json()
        trainer = _session(model_id)
        return _with_seq(model_id, body, lambda: (trainer.load_state(body["path"]), {"ok": True})[1])

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
        return {"status": "ok", "sessions": str(len(sessions)), "max_sessions": str(max_sessions)}

    return app


def main() -> None:
    """Pod entrypoint: serve the real GPU LoRA trainer + (configured) sampler."""
    import uvicorn

    from .trainers.base import Sampler
    from .trainers.lora import make_lora_trainer

    base_model = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
    blob_root = os.environ.get("OPEN_TINKER_BLOB_ROOT")

    # Sampler backend, in preference order:
    #   0. RemoteVLLMSampler (M3 hybrid split) when OPEN_TINKER_SAMPLER_ENDPOINT_ID
    #      is set — this control plane is then a CPU-only box that forwards
    #      sample/logprobs to the autoscaled serverless endpoint (no local model).
    #   1. vLLM in-process (perf; GPU-rich single pod) if vllm is installed
    #   2. HF transformers sampler (lazy load; reuses the training pod's own deps)
    # The local samplers load the base model lazily, so server startup stays fast
    # and a training-only run never pays for a sampler it doesn't use.
    sampler: Sampler
    endpoint_id = os.environ.get("OPEN_TINKER_SAMPLER_ENDPOINT_ID")
    if endpoint_id:
        from .sampler_worker import RemoteVLLMSampler

        sampler = RemoteVLLMSampler(endpoint_id)
    else:
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
