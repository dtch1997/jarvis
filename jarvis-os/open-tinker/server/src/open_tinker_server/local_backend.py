"""``LocalBackend`` — in-process implementation of the client's ``Backend``.

Injecting this into ``open_tinker.ServiceClient(backend=...)`` runs the whole
stack in ONE process with no HTTP and no request serialization: ``forward_backward``
hands the typed ``Datum`` objects straight to a ``Trainer`` (the heavy tensors
never hit JSON), and only the small response dicts are decoded back to typed SDK
objects. Same engines as the control plane (``app.py``), just called directly —
ideal for fast integration tests and single-process embedding.

This lives in the server package (not the light client) because it needs the
server's ``Trainer``/``Sampler`` engines + blob store; it depends on the client
only for the ``Backend`` contract + the shared codecs.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from open_tinker import types
from open_tinker._serialize import (
    decode_forward_backward_output,
    decode_logprobs,
    decode_sample_response,
    encode_model_input,
)
from open_tinker.protocol import Sampler, Trainer

from .blobstore import BlobStore

TrainerFactory = Callable[[str, Dict[str, Any], BlobStore], Trainer]


class LocalBackend:
    """Conforms to ``open_tinker.protocol.Backend`` (structurally)."""

    def __init__(
        self,
        trainer_factory: TrainerFactory,
        sampler: Sampler,
        blob_root: str = "/tmp/open-tinker-blobs",
    ):
        self._trainer_factory = trainer_factory
        self._sampler = sampler
        self._store = BlobStore(blob_root)
        self._sessions: Dict[str, Trainer] = {}
        self._n = 0

    def _session(self, model_id: str) -> Trainer:
        if model_id not in self._sessions:
            raise KeyError(f"no such session {model_id}")
        return self._sessions[model_id]

    # --- session ------------------------------------------------------------
    def create_session(
        self,
        base_model: Optional[str],
        lora: Optional[Dict[str, Any]],
        from_state: Optional[str] = None,
        user_metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        self._n += 1
        run_id = f"run-{self._n:06d}"
        body = {"base_model": base_model, "lora": lora, "from_state": from_state}
        trainer = self._trainer_factory(run_id, body, self._store)
        self._sessions[run_id] = trainer
        return {"model_id": run_id, "base_model": trainer.base_model}

    # --- training (typed Datum straight to the engine — no serialization) ---
    def forward_backward(
        self,
        model_id: str,
        data: List[types.Datum],
        loss_fn: str,
        loss_fn_config: Optional[Dict[str, float]] = None,
    ) -> types.ForwardBackwardOutput:
        body = self._session(model_id).forward_backward(data, loss_fn, loss_fn_config)
        return decode_forward_backward_output(body)

    def optim_step(self, model_id: str, adam_params: types.AdamParams) -> types.OptimStepResponse:
        body = self._session(model_id).optim_step(adam_params.model_dump())
        return types.OptimStepResponse(**body)

    def save(
        self, model_id: str, kind: str, name: str, ttl_seconds: Optional[int], overwrite: bool
    ) -> types.SaveWeightsResponse:
        path = self._session(model_id).save(kind, name, ttl_seconds, overwrite)
        self._store.set_ttl(path, ttl_seconds)
        return types.SaveWeightsResponse(path=path)

    def load_state(self, model_id: str, path: str) -> None:
        self._session(model_id).load_state(path)

    # --- sampling -----------------------------------------------------------
    def sample(
        self,
        model: str,
        weights_path: Optional[str],
        prompt: types.ModelInput,
        num_samples: int,
        sampling_params: types.SamplingParams,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
    ) -> types.SampleResponse:
        req = {
            "model": model,
            "weights_path": weights_path,
            "prompt": encode_model_input(prompt),
            "num_samples": num_samples,
            "sampling_params": sampling_params.model_dump(),
            "include_prompt_logprobs": include_prompt_logprobs,
            "topk_prompt_logprobs": topk_prompt_logprobs,
        }
        return decode_sample_response(self._sampler.sample(req))

    def compute_logprobs(
        self, model: str, weights_path: Optional[str], prompt: types.ModelInput
    ) -> List[Optional[float]]:
        req = {"model": model, "weights_path": weights_path, "prompt": encode_model_input(prompt)}
        return decode_logprobs(self._sampler.compute_logprobs(req))

    def capabilities(self) -> Dict[str, Any]:
        return {"models": [], "loss_fns": ["cross_entropy", "importance_sampling"], "local": True}
