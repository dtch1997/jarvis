"""Wire (de)serialization for the open-tinker protocol (spec §5 / WIRE_PROTOCOL.md).

JSON-friendly codecs for the value types that cross the wire. Tensors are sent as
raw little-endian buffers, base64-encoded, with explicit dtype+shape — compact
and exact (no float repr drift), which matters for the numerical-parity gate (#8).

``ModelInput`` is encoded as a flat token list: our scoped protocol only carries
text chunks (images are a spec non-goal), so ``{"tokens": [...]}`` is sufficient
and round-trips through ``ModelInput.from_ints`` / ``to_ints``.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import numpy as np

from .types import (
    Datum,
    ForwardBackwardOutput,
    ModelInput,
    SampledSequence,
    SampleResponse,
    TensorData,
)

__all__ = [
    "encode_tensor",
    "decode_tensor",
    "encode_model_input",
    "decode_model_input",
    "encode_datum",
    "decode_forward_backward_output",
    "decode_sample_response",
]

_NP = {"int64": np.int64, "float32": np.float32}


# --- TensorData -------------------------------------------------------------
def encode_tensor(t: TensorData) -> Dict[str, Any]:
    arr = np.ascontiguousarray(t._numpy)
    return {
        "dtype": t.dtype,
        "shape": list(t.shape) if t.shape is not None else list(arr.shape),
        "data_b64": base64.b64encode(arr.tobytes()).decode("ascii"),
        "sparse_crow_indices": t.sparse_crow_indices,
        "sparse_col_indices": t.sparse_col_indices,
    }


def decode_tensor(d: Dict[str, Any]) -> TensorData:
    dtype = d["dtype"]
    buf = base64.b64decode(d["data_b64"])
    arr = np.frombuffer(buf, dtype=_NP[dtype]).copy()  # copy → writable
    shape = d.get("shape")
    crow = d.get("sparse_crow_indices")
    col = d.get("sparse_col_indices")
    if crow is None and shape is not None and list(arr.shape) != list(shape):
        arr = arr.reshape(shape)
    return TensorData(
        data=arr,
        dtype=dtype,
        shape=shape,
        sparse_crow_indices=crow,
        sparse_col_indices=col,
    )


# --- ModelInput -------------------------------------------------------------
def encode_model_input(mi: ModelInput) -> Dict[str, Any]:
    return {"tokens": mi.to_ints()}


def decode_model_input(d: Dict[str, Any]) -> ModelInput:
    return ModelInput.from_ints(d["tokens"])


# --- Datum ------------------------------------------------------------------
def encode_datum(datum: Datum) -> Dict[str, Any]:
    return {
        "model_input": encode_model_input(datum.model_input),
        "loss_fn_inputs": {k: encode_tensor(v) for k, v in datum.loss_fn_inputs.items()},
    }


def decode_datum(d: Dict[str, Any]) -> Datum:
    return Datum(
        model_input=decode_model_input(d["model_input"]),
        loss_fn_inputs={k: decode_tensor(v) for k, v in d["loss_fn_inputs"].items()},
    )


# --- responses --------------------------------------------------------------
def decode_forward_backward_output(d: Dict[str, Any]) -> ForwardBackwardOutput:
    return ForwardBackwardOutput(
        loss_fn_output_type=d.get("loss_fn_output_type", "ArrayRecord"),
        loss_fn_outputs=[
            {k: decode_tensor(v) for k, v in rec.items()} for rec in d.get("loss_fn_outputs", [])
        ],
        metrics=d.get("metrics", {}),
    )


def _np_or_none(values: Optional[List[Optional[float]]]) -> Optional[np.ndarray]:
    """List with ``None`` holes → float32 array with ``NaN`` at the holes.

    This preserves the SDK's ``prompt_logprobs`` convention end-to-end: ``NaN``
    in the numpy buffer surfaces as ``None`` in the Python-list property.
    """
    if values is None:
        return None
    return np.array([np.nan if v is None else v for v in values], dtype=np.float32)


def decode_sample_response(d: Dict[str, Any]) -> SampleResponse:
    sequences = [
        SampledSequence(
            stop_reason=seq.get("stop_reason", "stop"),
            _tokens_list=list(seq["tokens"]),
            _logprobs_list=(list(seq["logprobs"]) if seq.get("logprobs") is not None else None),
        )
        for seq in d["sequences"]
    ]
    return SampleResponse(
        sequences=sequences,
        prompt_logprobs_np=_np_or_none(d.get("prompt_logprobs")),
    )


def decode_logprobs(d: Dict[str, Any]) -> List[Optional[float]]:
    return list(d["logprobs"])
