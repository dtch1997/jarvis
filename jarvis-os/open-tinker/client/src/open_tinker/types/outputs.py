"""Response / output types returned by the clients.

``SampleResponse`` / ``SampledSequence`` reproduce the SDK's dual numpy-array /
lazy-Python-list access, and crucially the ``prompt_logprobs`` convention:
``NaN`` in the numpy buffer becomes ``None`` in the Python list at positions
where a logprob was not computed (e.g. the first prompt token). ``battery``'s
prompted-teacher ``[S+1:]`` re-alignment depends on this convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Dict, List, Optional, Sequence

import numpy as np
from pydantic import BaseModel
from typing_extensions import Literal, TypeAlias

from .tensors import TensorData

__all__ = [
    "StopReason",
    "SampledSequence",
    "SampleResponse",
    "ForwardBackwardOutput",
    "OptimStepResponse",
    "SaveWeightsResponse",
]

StopReason: TypeAlias = Literal["length", "stop"]


@dataclass(frozen=True)
class SampledSequence:
    stop_reason: StopReason
    tokens_np: Optional[np.ndarray] = field(default=None, repr=False)
    logprobs_np: Optional[np.ndarray] = field(default=None, repr=False)
    _tokens_list: Optional[List[int]] = field(default=None, repr=False)
    _logprobs_list: Optional[List[float]] = field(default=None, repr=False)

    @cached_property
    def tokens(self) -> List[int]:
        if self._tokens_list is not None:
            return self._tokens_list
        if self.tokens_np is not None:
            return self.tokens_np.tolist()
        return []

    @cached_property
    def logprobs(self) -> Optional[List[float]]:
        if self._logprobs_list is not None:
            return self._logprobs_list
        if self.logprobs_np is not None:
            return self.logprobs_np.tolist()
        return None


@dataclass(frozen=True)
class SampleResponse:
    sequences: Sequence[SampledSequence]
    prompt_logprobs_np: Optional[np.ndarray] = field(default=None, repr=False)
    _prompt_logprobs_list: Optional[List[Optional[float]]] = field(default=None, repr=False)

    @cached_property
    def prompt_logprobs(self) -> Optional[List[Optional[float]]]:
        if self._prompt_logprobs_list is not None:
            return self._prompt_logprobs_list
        if self.prompt_logprobs_np is not None:
            result: List[Optional[float]] = self.prompt_logprobs_np.tolist()
            for i in np.flatnonzero(np.isnan(self.prompt_logprobs_np)):
                result[i] = None
            return result
        return None


@dataclass(frozen=True)
class ForwardBackwardOutput:
    loss_fn_output_type: str
    loss_fn_outputs: List[Dict[str, TensorData]]
    metrics: Dict[str, float] = field(default_factory=dict)


class OptimStepResponse(BaseModel):
    metrics: Optional[Dict[str, float]] = None


class SaveWeightsResponse(BaseModel):
    path: str
    """A ``tinker://`` URI for model weights at a specific step."""
    type: Optional[Literal["save_weights"]] = None
