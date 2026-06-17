"""``TrainingClient`` — the stateful training handle.

Transport-agnostic: it delegates every op to an injected
:class:`~open_tinker.protocol.Backend` (``HTTPBackend`` over the wire, or the
server's in-process ``LocalBackend``) and only owns the SDK ergonomics — the
``APIFuture`` shape and **submission ordering**. A single-thread executor per
client serializes submissions FIFO, so an ``optim_step`` enqueued after a
microbatch's ``forward_backward`` calls always runs after them.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Dict, List

from .. import types
from .._futures import APIFuture, AwaitableConcurrentFuture
from ..protocol import Backend

if TYPE_CHECKING:
    from .sampling_client import SamplingClient

__all__ = ["TrainingClient"]


class TrainingClient:
    def __init__(self, backend: Backend, model_id: types.ModelID, base_model: str):
        self._backend = backend
        self._model_id = model_id
        self._base_model = base_model
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"ot-train-{model_id}")

    def _submit(self, fn) -> AwaitableConcurrentFuture:
        return AwaitableConcurrentFuture(self._executor.submit(fn))

    # --- gradient computation ----------------------------------------------
    def forward_backward(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        return self._submit(
            lambda: self._backend.forward_backward(self._model_id, data, loss_fn, loss_fn_config)
        )

    async def forward_backward_async(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        return self.forward_backward(data, loss_fn, loss_fn_config)

    # --- forward-only (planned) --------------------------------------------
    def forward(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        """Forward pass without backward — planned. The cookbook's SFT eval uses
        ``SamplingClient.compute_logprobs`` instead; add a ``Backend.forward`` +
        server hook when an eval path needs it."""
        raise NotImplementedError(
            "TrainingClient.forward (forward-only) is not implemented yet; "
            "use SamplingClient.compute_logprobs for scoring."
        )

    async def forward_async(self, *args, **kwargs) -> APIFuture[types.ForwardBackwardOutput]:
        raise NotImplementedError("TrainingClient.forward_async is not implemented yet.")

    # --- optimizer ----------------------------------------------------------
    def optim_step(self, adam_params: types.AdamParams) -> APIFuture[types.OptimStepResponse]:
        return self._submit(lambda: self._backend.optim_step(self._model_id, adam_params))

    async def optim_step_async(
        self, adam_params: types.AdamParams
    ) -> APIFuture[types.OptimStepResponse]:
        return self.optim_step(adam_params)

    # --- checkpoints --------------------------------------------------------
    def save_state(
        self, name: str, ttl_seconds: int | None = None, overwrite: bool = False
    ) -> APIFuture[types.SaveWeightsResponse]:
        """Persist full training state (incl. optimizer) → ``tinker://.../weights/...``."""
        return self._submit(
            lambda: self._backend.save(self._model_id, "state", name, ttl_seconds, overwrite)
        )

    async def save_state_async(
        self, name: str, ttl_seconds: int | None = None, overwrite: bool = False
    ) -> APIFuture[types.SaveWeightsResponse]:
        return self.save_state(name, ttl_seconds, overwrite)

    def save_weights_for_sampler(
        self, name: str, ttl_seconds: int | None = None
    ) -> APIFuture[types.SaveWeightsResponse]:
        """Persist inference-only adapter weights → ``tinker://.../sampler_weights/...``."""
        return self._submit(
            lambda: self._backend.save(self._model_id, "sampler", name, ttl_seconds, False)
        )

    async def save_weights_for_sampler_async(
        self, name: str, ttl_seconds: int | None = None
    ) -> APIFuture[types.SaveWeightsResponse]:
        return self.save_weights_for_sampler(name, ttl_seconds)

    def load_state(self, path: str) -> APIFuture[None]:
        """Restore full training state from a ``tinker://.../weights/...`` path."""
        return self._submit(lambda: self._backend.load_state(self._model_id, path))

    async def load_state_async(self, path: str) -> None:
        return self.load_state(path).result()

    def save_weights_and_get_sampling_client(
        self, name: str | None = None, retry_config: object | None = None
    ) -> "SamplingClient":
        # ``name`` is optional to match the real SDK, where it is deprecated and has no
        # effect — checkpoints are ephemeral and auto-named. The cookbook's RL/distill
        # loops (rl.train, distillation.train_on_policy) call this with NO args every
        # step (issue #21 task 5), so a required name broke on-policy training. Auto-name
        # uniquely so each step's adapter lands at a distinct sampler_weights path.
        from .sampling_client import SamplingClient

        if name is None:
            import uuid

            name = f"sampler-{uuid.uuid4().hex[:12]}"
        resp = self.save_weights_for_sampler(name).result()
        return SamplingClient(self._backend, model=self._base_model, weights_path=resp.path)

    async def save_weights_and_get_sampling_client_async(
        self, name: str | None = None, retry_config: object | None = None
    ) -> "SamplingClient":
        return self.save_weights_and_get_sampling_client(name)

    def create_sampling_client(
        self, model_path: str, retry_config: object | None = None
    ) -> "SamplingClient":
        # Create a sampling client from ALREADY-SAVED weights — matches the real SDK.
        # The cookbook's RL loop saves a checkpoint, then calls this with the returned
        # ``tinker://`` path (rl.train save_periodic). Treating the arg as a *name* and
        # re-saving (the old behaviour) double-prefixed the path -> 500 (issue #21 task 5).
        from .sampling_client import SamplingClient

        weights = model_path if (model_path and model_path.startswith("tinker://")) else None
        return SamplingClient(self._backend, model=self._base_model, weights_path=weights)

    async def create_sampling_client_async(
        self, model_path: str, retry_config: object | None = None
    ) -> "SamplingClient":
        return self.create_sampling_client(model_path)

    # --- info / tokenizer ---------------------------------------------------
    def get_tokenizer(self):
        """HF tokenizer for the base model (parity w/ cookbook renderers)."""
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(self._base_model)

    def get_info(self):
        return {"model_id": self._model_id, "base_model": self._base_model}
