"""``RestClient`` — REST operations over training runs / checkpoints.

The cookbook obtains one via ``ServiceClient.create_rest_client()`` and uses a
small set of methods (checkpoint lookup/delete, audit log). Construction is
offline; method bodies are stubbed until the control plane's REST surface lands
(spec §5, task #4). Signatures match the real SDK subset the cookbook calls.
"""

from __future__ import annotations

from typing import Any

from ..._transport import Transport

__all__ = ["RestClient"]

_STUB = "open-tinker RestClient.{op} not implemented yet (blocked on control plane #4)."


class RestClient:
    def __init__(self, transport: Transport):
        self._transport = transport

    def get_training_run_by_tinker_path(self, tinker_path: str) -> Any:
        raise NotImplementedError(_STUB.format(op="get_training_run_by_tinker_path"))

    async def get_training_run_by_tinker_path_async(self, tinker_path: str) -> Any:
        raise NotImplementedError(_STUB.format(op="get_training_run_by_tinker_path_async"))

    def delete_checkpoint_from_tinker_path(self, tinker_path: str) -> Any:
        raise NotImplementedError(_STUB.format(op="delete_checkpoint_from_tinker_path"))

    async def delete_checkpoint_from_tinker_path_async(self, tinker_path: str) -> None:
        raise NotImplementedError(_STUB.format(op="delete_checkpoint_from_tinker_path_async"))

    def list_checkpoints(self, training_run_id: str) -> Any:
        raise NotImplementedError(_STUB.format(op="list_checkpoints"))

    def get_audit_log(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(_STUB.format(op="get_audit_log"))
