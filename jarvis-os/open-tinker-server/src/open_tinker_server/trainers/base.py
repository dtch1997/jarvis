"""Backend interfaces the control plane routes to.

``Trainer`` is the stateful training-session engine (one instance per ``model_id``,
living on a GPU pod, holding model+optimizer in VRAM). ``Sampler`` is the
stateless generation/scoring engine (vLLM worker). The control plane (``app.py``)
speaks the wire protocol and delegates to whichever implementation is registered,
so the same HTTP surface works for the ``Fake*`` backends (CPU/CI) and the real
``LoRATrainer`` / vLLM sampler (pod).

All payloads are the decoded wire dicts (WIRE_PROTOCOL.md). Trainers receive
already-decoded ``Datum`` objects via ``open_tinker._serialize``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable

from open_tinker.types import Datum


@runtime_checkable
class Trainer(Protocol):
    """One training session. Methods mirror the wire ops for a single model_id."""

    base_model: str

    def forward_backward(
        self, data: List[Datum], loss_fn: str, loss_fn_config: Dict[str, float] | None
    ) -> Dict[str, Any]:
        """Accumulate gradients for one microbatch. Returns the wire body
        ``{loss_fn_output_type, loss_fn_outputs, metrics}``."""

    def optim_step(self, adam_params: Dict[str, float]) -> Dict[str, Any]:
        """Apply one Adam update over accumulated grads, then zero them.
        Returns ``{metrics}``."""

    def save(self, kind: str, name: str, ttl_seconds: int | None, overwrite: bool) -> str:
        """Persist ``state`` or ``sampler`` weights; return a ``tinker://`` path."""

    def load_state(self, path: str) -> None: ...


@runtime_checkable
class Sampler(Protocol):
    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]: ...

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]: ...
