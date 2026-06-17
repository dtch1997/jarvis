"""``ServiceClient`` — entry point, mirroring ``tinker.ServiceClient``.

The cookbook constructs it as ``tinker.ServiceClient(base_url=..., api_key=...)``
(sometimes argless). It resolves to a :class:`~open_tinker.protocol.Backend`:
by default an ``HTTPBackend`` over the wire, but you can inject any Backend —
notably the server's in-process ``LocalBackend`` — via ``backend=...`` for a
single-process, no-socket mode.

``create_lora_training_client`` allocates a training session and returns a
stateful ``TrainingClient``; ``create_sampling_client`` returns a stateless
``SamplingClient``. Construction is side-effect-free (no network).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .._config import resolve_config
from .._transport import Handler, Transport
from ..backends import HTTPBackend
from ..protocol import Backend
from .sampling_client import SamplingClient
from .training_client import TrainingClient

if TYPE_CHECKING:
    from ..lib.public_interfaces.rest_client import RestClient

__all__ = ["ServiceClient"]


class ServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        user_metadata: dict[str, str] | None = None,
        project_id: str | None = None,
        handler: Optional[Handler] = None,
        http_client: Any = None,
        backend: Optional[Backend] = None,
        **kwargs: Any,
    ):
        self._user_metadata = user_metadata
        self._project_id = project_id
        # Injected backend wins (e.g. LocalBackend); otherwise build an HTTPBackend.
        # ``_transport`` is kept only for the HTTP path (RestClient lookups).
        if backend is not None:
            self._backend = backend
            self._transport = None
        else:
            self._transport = Transport(
                resolve_config(base_url=base_url, api_key=api_key),
                handler=handler,
                http_client=http_client,
            )
            self._backend = HTTPBackend(self._transport)

    def create_lora_training_client(
        self,
        base_model: str,
        rank: int = 32,
        seed: int | None = None,
        train_mlp: bool = True,
        train_attn: bool = True,
        train_unembed: bool = True,
        user_metadata: dict[str, str] | None = None,
    ) -> TrainingClient:
        lora = {
            "rank": rank,
            "seed": seed,
            "train_mlp": train_mlp,
            "train_attn": train_attn,
            "train_unembed": train_unembed,
        }
        body = self._backend.create_session(base_model, lora, None, user_metadata)
        return TrainingClient(self._backend, model_id=body["model_id"], base_model=base_model)

    async def create_lora_training_client_async(self, *args: Any, **kwargs: Any) -> TrainingClient:
        return self.create_lora_training_client(*args, **kwargs)

    def create_training_client_from_state(self, path: str) -> TrainingClient:
        """Resume a training client from a full-state ``tinker://`` checkpoint."""
        from .. import types

        parsed = types.ParsedCheckpointTinkerPath.from_tinker_path(path)
        body = self._backend.create_session(None, None, path, None)
        base_model = body.get("base_model", parsed.training_run_id)
        return TrainingClient(self._backend, model_id=body["model_id"], base_model=base_model)

    def create_sampling_client(
        self,
        base_model: str | None = None,
        model_path: str | None = None,
    ) -> SamplingClient:
        model = base_model or model_path
        if model is None:
            raise ValueError("create_sampling_client requires base_model or model_path")
        weights = model_path if (model_path and model_path.startswith("tinker://")) else None
        return SamplingClient(self._backend, model=model, weights_path=weights)

    def create_rest_client(self) -> "RestClient":
        from ..lib.public_interfaces.rest_client import RestClient

        if self._transport is None:
            raise NotImplementedError("create_rest_client requires the HTTP backend.")
        return RestClient(self._transport)

    def get_server_capabilities(self) -> dict:
        """Models / loss fns the backend supports (cookbook probes this)."""
        return self._backend.capabilities()
