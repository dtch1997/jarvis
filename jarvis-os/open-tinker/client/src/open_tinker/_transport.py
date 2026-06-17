"""HTTP transport to the control plane (spec §5 / WIRE_PROTOCOL.md).

Thin synchronous JSON-over-HTTP client. ``ServiceClient`` owns one ``Transport``;
the training/sampling clients borrow it and layer their own concurrency
(futures/executors) on top — see ``clients/``.

Testability: a ``handler`` callable ``(method, path, json) -> (status, body)`` can
be injected to run the protocol fully in-process (used by the mock-server tests),
so the client + serialization are exercised without a live backend.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from ._config import ClientConfig
from ._exceptions import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

__all__ = ["Transport", "ENDPOINTS"]

# Client-side mirror of spec §5. Values are (method, path-template).
ENDPOINTS: Dict[str, Tuple[str, str]] = {
    "create_session": ("POST", "/v1/training/sessions"),
    "forward_backward": ("POST", "/v1/training/{model_id}/forward_backward"),
    "optim_step": ("POST", "/v1/training/{model_id}/optim_step"),
    "save": ("POST", "/v1/training/{model_id}/save"),
    "load_state": ("POST", "/v1/training/{model_id}/load_state"),
    "sample": ("POST", "/v1/sample"),
    "logprobs": ("POST", "/v1/logprobs"),
    "capabilities": ("GET", "/v1/capabilities"),
}

_STATUS_TO_EXC = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
    500: InternalServerError,
}

# In-process handler signature for tests: (method, path, json_body) -> (status, body).
Handler = Callable[[str, str, Dict[str, Any]], Tuple[int, Dict[str, Any]]]


class Transport:
    def __init__(
        self,
        config: ClientConfig,
        handler: Optional[Handler] = None,
        http_client: Any = None,
    ):
        self.config = config
        self._handler = handler
        # An injected httpx.Client (e.g. one wrapping an ASGITransport) lets tests
        # drive a real server app over the full JSON path without a socket.
        self._client = http_client

    def _http(self):
        if self._client is None:
            import httpx

            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            self._client = httpx.Client(
                base_url=self.config.base_url, headers=headers, timeout=600.0
            )
        return self._client

    def request(
        self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **path_params: str
    ) -> Dict[str, Any]:
        method, template = ENDPOINTS[endpoint]
        path = template.format(**path_params)
        payload = payload or {}

        if self._handler is not None:
            status, body = self._handler(method, path, payload)
        else:
            try:
                resp = self._http().request(method, path, json=payload)
            except Exception as e:  # noqa: BLE001 — surface as connection error
                raise APIConnectionError(str(e)) from e
            status = resp.status_code
            if resp.content:
                try:
                    body = resp.json()
                except ValueError:
                    # Non-JSON body (e.g. a proxy 502/504 HTML page or a gateway
                    # timeout). Surface it as a clear status error, not a decode crash.
                    raise APIStatusError(
                        f"non-JSON response (status {status}): {resp.text[:200]}",
                        status_code=status,
                    ) from None
            else:
                body = {}

        if status >= 400:
            message = body.get("error", body) if isinstance(body, dict) else str(body)
            exc_cls = _STATUS_TO_EXC.get(status, APIStatusError)
            raise exc_cls(f"{message}", status_code=status)
        return body
