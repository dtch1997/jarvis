"""``TrainingClient`` — the stateful training handle.

Signatures mirror the real SDK (the subset the cookbook + battery call). Behind
them is a long-lived GPU daemon holding base model + LoRA adapter + Adam state in
VRAM (spec §4.1 C): N×``forward_backward`` accumulate gradients, one
``optim_step`` applies Adam and zeroes them.

**Ordering.** The SDK's submit-now/await-later model lets the cookbook pipeline
many ``forward_backward`` calls before an ``optim_step``. We preserve both the
shape (every call returns an ``APIFuture``) and the ordering by running each
client's requests through a single-thread executor: submissions queue FIFO, so an
``optim_step`` enqueued after the microbatch's ``forward_backward`` calls always
runs after them. A monotonic ``seq_id`` is attached for server-side idempotency.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Dict, List

from .. import types
from .._futures import APIFuture, AwaitableConcurrentFuture
from .._serialize import decode_forward_backward_output, encode_datum
from .._transport import Transport

if TYPE_CHECKING:
    from .sampling_client import SamplingClient

__all__ = ["TrainingClient"]


class TrainingClient:
    def __init__(self, transport: Transport, model_id: types.ModelID, base_model: str):
        self._transport = transport
        self._model_id = model_id
        self._base_model = base_model
        # maxworkers=1 → FIFO; preserves forward_backward → optim_step ordering.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"ot-train-{model_id}")
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _submit(self, fn) -> AwaitableConcurrentFuture:
        return AwaitableConcurrentFuture(self._executor.submit(fn))

    # --- gradient computation ----------------------------------------------
    def forward_backward(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        seq_id = self._next_seq()
        payload = {
            "seq_id": seq_id,
            "loss_fn": loss_fn,
            "loss_fn_config": loss_fn_config,
            "data": [encode_datum(d) for d in data],
        }

        def _run():
            body = self._transport.request("forward_backward", payload, model_id=self._model_id)
            return decode_forward_backward_output(body)

        return self._submit(_run)

    async def forward_backward_async(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        # The real SDK's *_async returns the same future-like; callers await it.
        return self.forward_backward(data, loss_fn, loss_fn_config)

    # --- forward-only (planned) --------------------------------------------
    def forward(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        """Forward pass without backward (no grad accumulation) — planned.

        The real SDK exposes this for eval/scoring. Not wired yet: the cookbook's
        SFT eval path uses ``SamplingClient.compute_logprobs`` instead. Add the
        ``/v1/training/{model_id}/forward`` endpoint + server hook when needed.
        """
        raise NotImplementedError(
            "TrainingClient.forward (forward-only) is not implemented yet; "
            "use SamplingClient.compute_logprobs for scoring, or implement the forward endpoint."
        )

    async def forward_async(
        self,
        data: List[types.Datum],
        loss_fn: types.LossFnType,
        loss_fn_config: Dict[str, float] | None = None,
    ) -> APIFuture[types.ForwardBackwardOutput]:
        raise NotImplementedError("TrainingClient.forward_async is not implemented yet.")

    # --- optimizer ----------------------------------------------------------
    def optim_step(self, adam_params: types.AdamParams) -> APIFuture[types.OptimStepResponse]:
        seq_id = self._next_seq()
        payload = {"seq_id": seq_id, "adam_params": adam_params.model_dump()}

        def _run():
            body = self._transport.request("optim_step", payload, model_id=self._model_id)
            return types.OptimStepResponse(**body)

        return self._submit(_run)

    async def optim_step_async(
        self, adam_params: types.AdamParams
    ) -> APIFuture[types.OptimStepResponse]:
        return self.optim_step(adam_params)

    # --- checkpoints --------------------------------------------------------
    def _save(self, kind: str, name: str, ttl_seconds: int | None, overwrite: bool):
        seq_id = self._next_seq()
        payload = {
            "seq_id": seq_id,
            "kind": kind,
            "name": name,
            "ttl_seconds": ttl_seconds,
            "overwrite": overwrite,
        }

        def _run():
            body = self._transport.request("save", payload, model_id=self._model_id)
            return types.SaveWeightsResponse(**body)

        return self._submit(_run)

    def save_state(
        self, name: str, ttl_seconds: int | None = None, overwrite: bool = False
    ) -> APIFuture[types.SaveWeightsResponse]:
        """Persist full training state (incl. optimizer) → ``tinker://.../weights/...``."""
        return self._save("state", name, ttl_seconds, overwrite)

    async def save_state_async(
        self, name: str, ttl_seconds: int | None = None, overwrite: bool = False
    ) -> APIFuture[types.SaveWeightsResponse]:
        return self.save_state(name, ttl_seconds, overwrite)

    def save_weights_for_sampler(
        self, name: str, ttl_seconds: int | None = None
    ) -> APIFuture[types.SaveWeightsResponse]:
        """Persist inference-only adapter weights → ``tinker://.../sampler_weights/...``."""
        return self._save("sampler", name, ttl_seconds, False)

    async def save_weights_for_sampler_async(
        self, name: str, ttl_seconds: int | None = None
    ) -> APIFuture[types.SaveWeightsResponse]:
        return self.save_weights_for_sampler(name, ttl_seconds)

    def load_state(self, path: str) -> APIFuture[None]:
        """Restore full training state from a ``tinker://.../weights/...`` path."""
        seq_id = self._next_seq()
        payload = {"seq_id": seq_id, "path": path}

        def _run():
            self._transport.request("load_state", payload, model_id=self._model_id)
            return None

        return self._submit(_run)

    async def load_state_async(self, path: str) -> None:
        return self.load_state(path).result()

    def save_weights_and_get_sampling_client(self, name: str) -> "SamplingClient":
        from .sampling_client import SamplingClient

        resp = self.save_weights_for_sampler(name).result()
        return SamplingClient(self._transport, model=self._base_model, weights_path=resp.path)

    async def save_weights_and_get_sampling_client_async(self, name: str) -> "SamplingClient":
        return self.save_weights_and_get_sampling_client(name)

    def create_sampling_client(self, name: str) -> "SamplingClient":
        return self.save_weights_and_get_sampling_client(name)

    # --- info / tokenizer ---------------------------------------------------
    def get_tokenizer(self):
        """HF tokenizer for the base model (parity w/ cookbook renderers)."""
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(self._base_model)

    def get_info(self):
        return {"model_id": self._model_id, "base_model": self._base_model}
