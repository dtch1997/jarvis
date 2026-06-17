"""``open_tinker.types`` — the scoped subset of ``tinker.types`` our consumers use.

Re-exported flat so ``tinker.types.X`` references in ``tinker_cookbook`` and
``battery`` resolve after :func:`open_tinker.use_as_tinker`.
"""

from .checkpoint import Checkpoint, CheckpointType, ModelID, ParsedCheckpointTinkerPath
from .datum import Datum, LossFnInputs, LossFnOutput, LossFnType
from .model_input import (
    EncodedTextChunk,
    ImageAssetPointerChunk,
    ImageChunk,
    ModelInput,
    ModelInputChunk,
)
# Submodule alias so `from tinker.types.tensor_data import TensorData` resolves
# (the real SDK exposes types as submodules; the cookbook's rl_loop imports this).
from . import tensors as tensor_data  # noqa: F401
from .outputs import (
    ForwardBackwardOutput,
    OptimStepResponse,
    SampledSequence,
    SampleResponse,
    SaveWeightsResponse,
    StopReason,
)
from .params import AdamParams, LoraConfig, SamplingParams
from .tensors import TensorData, TensorDtype

__all__ = [
    "AdamParams",
    "Checkpoint",
    "CheckpointType",
    "Datum",
    "EncodedTextChunk",
    "ImageChunk",
    "ImageAssetPointerChunk",
    "ForwardBackwardOutput",
    "LossFnInputs",
    "LossFnOutput",
    "LossFnType",
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
]
