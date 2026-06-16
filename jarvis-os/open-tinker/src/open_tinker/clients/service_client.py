"""``ServiceClient`` — entry point, mirroring ``tinker.ServiceClient``.

The cookbook constructs it as ``tinker.ServiceClient(base_url=..., api_key=...)``
(sometimes argless). ``create_lora_training_client`` allocates a training session
on a GPU pod via the control plane and returns a stateful ``TrainingClient``;
``create_sampling_client`` returns a stateless ``SamplingClient`` for a base
model or a ``tinker://`` weights handle.

Construction is side-effect-free (no network). A ``handler`` may be injected to
run the whole protocol in-process for tests (see ``Transport``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .. import types
from .._config import resolve_config
from .._transport import Handler, Transport
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
        **kwargs: Any,
    ):
        self._config = resolve_config(base_url=base_url, api_key=api_key)
        self._user_metadata = user_metadata
        self._project_id = project_id
        self._transport = Transport(self._config, handler=handler, http_client=http_client)

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
        payload = {
            "base_model": base_model,
            "lora": {
                "rank": rank,
                "seed": seed,
                "train_mlp": train_mlp,
                "train_attn": train_attn,
                "train_unembed": train_unembed,
            },
            "from_state": None,
            "user_metadata": user_metadata,
        }
        body = self._transport.request("create_session", payload)
        return TrainingClient(self._transport, model_id=body["model_id"], base_model=base_model)

    async def create_lora_training_client_async(self, *args: Any, **kwargs: Any) -> TrainingClient:
        return self.create_lora_training_client(*args, **kwargs)

    def create_training_client_from_state(self, path: str) -> TrainingClient:
        """Resume a training client from a full-state ``tinker://`` checkpoint."""
        parsed = types.ParsedCheckpointTinkerPath.from_tinker_path(path)
        payload = {"base_model": None, "lora": None, "from_state": path, "user_metadata": None}
        body = self._transport.request("create_session", payload)
        base_model = body.get("base_model", parsed.training_run_id)
        return TrainingClient(self._transport, model_id=body["model_id"], base_model=base_model)

    def create_sampling_client(
        self,
        base_model: str | None = None,
        model_path: str | None = None,
    ) -> SamplingClient:
        model = base_model or model_path
        if model is None:
            raise ValueError("create_sampling_client requires base_model or model_path")
        weights = model_path if (model_path and model_path.startswith("tinker://")) else None
        return SamplingClient(self._transport, model=model, weights_path=weights)

    def create_rest_client(self) -> "RestClient":
        from ..lib.public_interfaces.rest_client import RestClient

        return RestClient(self._transport)

    def get_server_capabilities(self) -> dict:
        """Models / loss fns the backend supports (cookbook probes this)."""
        return self._transport.request("capabilities")
