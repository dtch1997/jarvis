"""``HTTPBackend`` — the over-the-wire :class:`~open_tinker.protocol.Backend`.

Owns all serialization and the per-session ``seq_id`` (wire-protocol details that
used to live in the clients). Typed args in → encode → ``Transport`` POST → decode
→ typed out. The clients are now transport-agnostic: they just call typed Backend
methods and wrap them in futures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .. import types
from .._serialize import (
    decode_forward_backward_output,
    decode_logprobs,
    decode_sample_response,
    encode_datum,
    encode_model_input,
)
from .._transport import Transport


class HTTPBackend:
    def __init__(self, transport: Transport):
        self._transport = transport
        self._seq: Dict[str, int] = {}

    def _next_seq(self, model_id: str) -> int:
        n = self._seq.get(model_id, 0) + 1
        self._seq[model_id] = n
        return n

    # --- session ------------------------------------------------------------
    def create_session(
        self,
        base_model: Optional[str],
        lora: Optional[Dict[str, Any]],
        from_state: Optional[str] = None,
        user_metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "base_model": base_model,
            "lora": lora,
            "from_state": from_state,
            "user_metadata": user_metadata,
        }
        return self._transport.request("create_session", payload)

    # --- training -----------------------------------------------------------
    def forward_backward(
        self,
        model_id: str,
        data: List[types.Datum],
        loss_fn: str,
        loss_fn_config: Optional[Dict[str, float]] = None,
    ) -> types.ForwardBackwardOutput:
        payload = {
            "seq_id": self._next_seq(model_id),
            "loss_fn": loss_fn,
            "loss_fn_config": loss_fn_config,
            "data": [encode_datum(d) for d in data],
        }
        body = self._transport.request("forward_backward", payload, model_id=model_id)
        return decode_forward_backward_output(body)

    def optim_step(self, model_id: str, adam_params: types.AdamParams) -> types.OptimStepResponse:
        payload = {"seq_id": self._next_seq(model_id), "adam_params": adam_params.model_dump()}
        body = self._transport.request("optim_step", payload, model_id=model_id)
        return types.OptimStepResponse(**body)

    def save(
        self, model_id: str, kind: str, name: str, ttl_seconds: Optional[int], overwrite: bool
    ) -> types.SaveWeightsResponse:
        payload = {
            "seq_id": self._next_seq(model_id),
            "kind": kind,
            "name": name,
            "ttl_seconds": ttl_seconds,
            "overwrite": overwrite,
        }
        body = self._transport.request("save", payload, model_id=model_id)
        return types.SaveWeightsResponse(**body)

    def load_state(self, model_id: str, path: str) -> None:
        payload = {"seq_id": self._next_seq(model_id), "path": path}
        self._transport.request("load_state", payload, model_id=model_id)

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
        payload = {
            "model": model,
            "weights_path": weights_path,
            "prompt": encode_model_input(prompt),
            "num_samples": num_samples,
            "sampling_params": sampling_params.model_dump(),
            "include_prompt_logprobs": include_prompt_logprobs,
            "topk_prompt_logprobs": topk_prompt_logprobs,
        }
        return decode_sample_response(self._transport.request("sample", payload))

    def compute_logprobs(
        self, model: str, weights_path: Optional[str], prompt: types.ModelInput
    ) -> List[Optional[float]]:
        payload = {"model": model, "weights_path": weights_path, "prompt": encode_model_input(prompt)}
        return decode_logprobs(self._transport.request("logprobs", payload))

    def capabilities(self) -> Dict[str, Any]:
        return self._transport.request("capabilities")
