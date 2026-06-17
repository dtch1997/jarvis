"""open-tinker — scoped, self-hosted reimplementation of the Tinker SDK.

Public surface mirrors the subset of ``tinker.__all__`` that ``tinker_cookbook``
and ``battery/train/tinker`` actually use (strategy C). Anything the real SDK
exports but our consumers never call is intentionally absent — task #2 (cookbook
import parity) is what catches gaps.
"""

from __future__ import annotations

from . import types as types
from ._exceptions import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    RequestFailedError,
    TinkerError,
    UnprocessableEntityError,
)
from ._futures import APIFuture
from ._version import __version__
from .backends import HTTPBackend
from .clients import SamplingClient, ServiceClient, TrainingClient
from .protocol import Backend, Sampler, Trainer
from .shim import use_as_tinker

# Commonly-used types re-exported flat, matching ``tinker``'s top-level names.
from .types import (
    AdamParams,
    Checkpoint,
    CheckpointType,
    Datum,
    EncodedTextChunk,
    ForwardBackwardOutput,
    LoraConfig,
    ModelID,
    ModelInput,
    ModelInputChunk,
    OptimStepResponse,
    ParsedCheckpointTinkerPath,
    SampledSequence,
    SampleResponse,
    SamplingParams,
    SaveWeightsResponse,
    StopReason,
    TensorData,
    TensorDtype,
)

__all__ = [
    # Core clients
    "ServiceClient",
    "TrainingClient",
    "SamplingClient",
    "APIFuture",
    # Backend seam (DI)
    "Backend",
    "HTTPBackend",
    "Trainer",
    "Sampler",
    # Commonly used types
    "AdamParams",
    "Checkpoint",
    "CheckpointType",
    "Datum",
    "EncodedTextChunk",
    "ForwardBackwardOutput",
    "LoraConfig",
    "ModelID",
    "ModelInput",
    "ModelInputChunk",
    "OptimStepResponse",
    "ParsedCheckpointTinkerPath",
    "SampledSequence",
    "SampleResponse",
    "SamplingParams",
    "SaveWeightsResponse",
    "StopReason",
    "TensorData",
    "TensorDtype",
    # Exceptions
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
    # Shim + types module
    "use_as_tinker",
    "types",
    "__version__",
]
