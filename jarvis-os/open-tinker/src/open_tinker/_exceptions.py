"""Exception hierarchy mirroring ``tinker``'s, so cookbook retry/except blocks
compile and behave. Names match the real SDK's ``__all__``.

Status-code subclasses carry an HTTP ``status_code`` like the original.
"""

from __future__ import annotations

__all__ = [
    "TinkerError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "APIConnectionError",
    "APIResponseValidationError",
    "RequestFailedError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "InternalServerError",
]


class TinkerError(Exception):
    """Base class for all open-tinker errors."""


class APIError(TinkerError):
    pass


class APIConnectionError(APIError):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIResponseValidationError(APIError):
    pass


class RequestFailedError(APIError):
    """A submitted request resolved to a failure on the backend."""


class APIStatusError(APIError):
    """An error response with an HTTP status code."""

    status_code: int = 0

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(APIStatusError):
    status_code = 400


class AuthenticationError(APIStatusError):
    status_code = 401


class PermissionDeniedError(APIStatusError):
    status_code = 403


class NotFoundError(APIStatusError):
    status_code = 404


class ConflictError(APIStatusError):
    status_code = 409


class UnprocessableEntityError(APIStatusError):
    status_code = 422


class RateLimitError(APIStatusError):
    status_code = 429


class InternalServerError(APIStatusError):
    status_code = 500
