"""``Datum`` plus the loss-function type aliases, faithful to ``tinker.types``.

``Datum.__post_init__`` coerces ``loss_fn_inputs`` values (torch tensors, numpy
arrays, or plain numeric lists) into ``TensorData``, applying the per-key wire
dtype and the sparse encoding for the two sparse-eligible keys — exactly the
behavior ``battery``'s on-policy distill loop relies on when it fills in
``advantages`` / ``logprobs`` / ``mask`` / ``target_tokens``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Union

import numpy as np
from typing_extensions import Literal, TypeAlias

from .model_input import ModelInput
from .tensors import TensorData

if TYPE_CHECKING:
    import torch  # noqa: TC004  (type-only; torch is imported lazily where needed)


def _is_torch_tensor(value: object) -> bool:
    """True if ``value`` is a torch tensor, without importing torch eagerly.

    Avoids loading torch at ``import open_tinker`` time — it's pulled in only when
    a torch tensor is actually being converted (i.e. during training, where torch
    is present anyway).
    """
    import sys

    torch = sys.modules.get("torch")
    return torch is not None and isinstance(value, torch.Tensor)

__all__ = ["Datum", "LossFnInputs", "LossFnOutput", "LossFnType"]

LossFnInputs: TypeAlias = Dict[str, TensorData]
LossFnOutput: TypeAlias = Dict[str, TensorData]

# The loss functions our backend implements: cross_entropy (M1 SFT + M2 off-policy
# soft targets) and importance_sampling (M2 on-policy distill). ppo/cispo/dro are
# declared for signature parity but are non-goals (no RL training in scope).
LossFnType: TypeAlias = Literal[
    "cross_entropy",
    "importance_sampling",
    "ppo",
    "cispo",
    "dro",
]

# Field-name → wire dtype for raw Python lists with no inferable numpy dtype.
_KEY_TO_TYPE = {
    "target_tokens": "int64",
    "weights": "float32",
    "advantages": "float32",
    "logprobs": "float32",
    "clip_low_threshold": "float32",
    "clip_high_threshold": "float32",
}
_SPARSE_ELIGIBLE_KEYS = {"target_tokens", "weights"}


def _maybe_convert(key: str, value: Union[TensorData, "torch.Tensor", np.ndarray, list]) -> TensorData:
    if isinstance(value, TensorData):
        return value
    if _is_torch_tensor(value):
        if key in _SPARSE_ELIGIBLE_KEYS and value.ndim == 2:
            return TensorData.from_torch_sparse(value)
        return TensorData.from_torch(value)
    if isinstance(value, np.ndarray):
        return TensorData.from_numpy(value)
    if isinstance(value, list):
        array = np.asarray(value)
        if array.dtype.kind in ("f", "i", "u"):
            target = _KEY_TO_TYPE.get(key, "float32")
            array = array.astype(np.int64 if target == "int64" else np.float32)
            return TensorData.from_numpy(array)
        raise ValueError(f"{key} must be a numeric array")
    raise TypeError(f"Unsupported loss_fn_inputs value for {key!r}: {type(value)}")


@dataclass(frozen=True)
class Datum:
    model_input: ModelInput
    loss_fn_inputs: LossFnInputs = field(default_factory=dict)

    def __post_init__(self) -> None:
        coerced: Dict[str, TensorData] = {
            key: _maybe_convert(key, value) for key, value in self.loss_fn_inputs.items()
        }
        object.__setattr__(self, "loss_fn_inputs", coerced)
