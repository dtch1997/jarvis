"""Shared, code-checked contracts for the open-tinker system (light package).

Three Protocols, all in the dependency-light client package so BOTH sides import
them without pulling heavy deps (the server depends on the client, never the
reverse):

- ``Backend`` — the operation seam the SDK clients call. Two implementations:
  ``HTTPBackend`` (over the wire, default) and the server's ``LocalBackend``
  (in-process, no socket / no request serialization). Injecting a ``LocalBackend``
  into ``ServiceClient`` gives a single-process mode — handy for fast integration
  tests and embedding.
- ``Trainer`` / ``Sampler`` — the server-side engine interfaces (one training
  session; one stateless sampler). Defined here so the client's ``LocalBackend``
  consumer and the server's concrete engines agree on one contract, and so
  ``WIRE_PROTOCOL.md`` is enforced by typing rather than prose.

``Backend`` speaks **typed** objects (``Datum``/``ModelInput``/``AdamParams`` in,
``ForwardBackwardOutput``/``SampleResponse`` out); serialization is an
implementation detail of ``HTTPBackend``. ``Trainer``/``Sampler`` speak the wire
dicts the control plane routes (so ``LocalBackend`` decodes their output, but the
heavy ``Datum`` tensors never get serialized on the in-process path).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from . import types


@runtime_checkable
class Backend(Protocol):
    """Where training/sampling operations execute, from the client's POV."""

    def create_session(
        self,
        base_model: Optional[str],
        lora: Optional[Dict[str, Any]],
        from_state: Optional[str] = None,
        user_metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Allocate/resume a training session → ``{"model_id", "base_model"}``."""

    def forward_backward(
        self,
        model_id: str,
        data: List[types.Datum],
        loss_fn: str,
        loss_fn_config: Optional[Dict[str, float]] = None,
    ) -> types.ForwardBackwardOutput: ...

    def optim_step(self, model_id: str, adam_params: types.AdamParams) -> types.OptimStepResponse: ...

    def save(
        self, model_id: str, kind: str, name: str, ttl_seconds: Optional[int], overwrite: bool
    ) -> types.SaveWeightsResponse: ...

    def load_state(self, model_id: str, path: str) -> None: ...

    def sample(
        self,
        model: str,
        weights_path: Optional[str],
        prompt: types.ModelInput,
        num_samples: int,
        sampling_params: types.SamplingParams,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
    ) -> types.SampleResponse: ...

    def compute_logprobs(
        self, model: str, weights_path: Optional[str], prompt: types.ModelInput
    ) -> List[Optional[float]]: ...

    def capabilities(self) -> Dict[str, Any]: ...


@runtime_checkable
class Trainer(Protocol):
    """One stateful training session (one ``model_id``), living on a GPU pod.

    Returns the wire bodies the control plane forwards (WIRE_PROTOCOL.md);
    ``data`` arrives as already-decoded ``Datum`` objects.
    """

    base_model: str

    def forward_backward(
        self, data: List[types.Datum], loss_fn: str, loss_fn_config: Optional[Dict[str, float]]
    ) -> Dict[str, Any]: ...

    def optim_step(self, adam_params: Dict[str, float]) -> Dict[str, Any]: ...

    def save(self, kind: str, name: str, ttl_seconds: Optional[int], overwrite: bool) -> str: ...

    def load_state(self, path: str) -> None: ...


@runtime_checkable
class Sampler(Protocol):
    """Stateless generation/scoring given a weights handle. Wire dict in/out."""

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]: ...

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]: ...
