"""``TensorData`` — wire-friendly tensor container, faithful to ``tinker.types``.

Mirrors the real SDK: a numpy-backed frozen container with ``from_torch`` /
``to_torch`` / ``from_numpy`` / ``to_numpy`` and optional CSR sparse encoding for
the two sparse-eligible loss keys (``target_tokens``, ``weights``). ``torch`` is
imported LAZILY so importing this package needs no torch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Union

import numpy as np
import numpy.typing as npt
from typing_extensions import Literal, TypeAlias

if TYPE_CHECKING:
    import torch  # noqa: TC004  (type-only; torch is imported lazily at call sites)

__all__ = ["TensorData", "TensorDtype"]

# Public wire dtype is intentionally narrow — float32 | int64 — matching the SDK.
TensorDtype: TypeAlias = Literal["int64", "float32"]

_TENSOR_TO_NUMPY = {"int64": np.int64, "float32": np.float32}
_NUMPY_KIND_TO_TENSOR = {"i": "int64", "u": "int64", "f": "float32"}


def _to_numpy_dtype(dtype: TensorDtype) -> np.dtype:
    if dtype not in _TENSOR_TO_NUMPY:
        raise ValueError(f"Unsupported TensorDtype {dtype!r}")
    return np.dtype(_TENSOR_TO_NUMPY[dtype])


def _numpy_to_tensor_dtype(dtype: np.dtype) -> TensorDtype:
    kind = dtype.kind
    if kind not in _NUMPY_KIND_TO_TENSOR:
        raise ValueError(f"Cannot represent numpy dtype {dtype!r} as a TensorDtype")
    return _NUMPY_KIND_TO_TENSOR[kind]  # type: ignore[return-value]


@dataclass(frozen=True, eq=False, init=False)
class TensorData:
    """Numpy-backed tensor with optional CSR sparse encoding.

    Field layout matches the real SDK so serialization is interchangeable:
    ``dtype``, ``shape``, ``sparse_crow_indices``, ``sparse_col_indices`` plus a
    private dense ``_numpy`` buffer.
    """

    dtype: TensorDtype
    shape: Optional[List[int]] = None
    sparse_crow_indices: Optional[List[int]] = None
    sparse_col_indices: Optional[List[int]] = None
    _numpy: np.ndarray = field(repr=False)

    def __init__(
        self,
        data: Union[List[int], List[float], np.ndarray, None] = None,
        dtype: Optional[TensorDtype] = None,
        shape: Optional[List[int]] = None,
        sparse_crow_indices: Optional[List[int]] = None,
        sparse_col_indices: Optional[List[int]] = None,
    ) -> None:
        if dtype is None:
            raise TypeError("TensorData requires `dtype`")
        np_dtype = _to_numpy_dtype(dtype)
        if isinstance(data, np.ndarray):
            arr = data.astype(np_dtype) if data.dtype != np_dtype else (
                data if data.flags.writeable else data.copy()
            )
        elif data is None:
            arr = np.empty(0, dtype=np_dtype)
        else:
            arr = np.asarray(data, dtype=np_dtype)
        if sparse_crow_indices is None and shape is not None and list(arr.shape) != shape:
            arr = arr.reshape(shape)
        object.__setattr__(self, "dtype", dtype)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "sparse_crow_indices", sparse_crow_indices)
        object.__setattr__(self, "sparse_col_indices", sparse_col_indices)
        object.__setattr__(self, "_numpy", arr)

    # --- constructors -------------------------------------------------------
    @classmethod
    def from_numpy(cls, array: npt.NDArray[Any]) -> "TensorData":
        return cls(
            data=array,
            dtype=_numpy_to_tensor_dtype(array.dtype),
            shape=list(array.shape),
        )

    @classmethod
    def from_torch(cls, tensor: "torch.Tensor") -> "TensorData":
        import torch

        if tensor.dtype == torch.bfloat16:
            arr = tensor.float().contiguous().numpy()
        else:
            arr = tensor.contiguous().numpy()
        return cls.from_numpy(arr)

    @classmethod
    def from_torch_sparse(cls, tensor: "torch.Tensor") -> "TensorData":
        """CSR-encode a dense 2-D tensor when it saves space, else fall back."""
        if tensor.ndim != 2:
            return cls.from_torch(tensor)
        nnz = int(tensor.count_nonzero().item())
        dense_size = tensor.shape[0] * tensor.shape[1]
        csr_size = (tensor.shape[0] + 1) + 2 * nnz
        if csr_size >= dense_size:
            return cls.from_torch(tensor)
        sparse_csr = tensor.to_sparse_csr()
        dtype = _numpy_to_tensor_dtype(np.dtype(sparse_csr.values().numpy().dtype))
        return cls(
            data=sparse_csr.values().numpy(),
            dtype=dtype,
            shape=list(tensor.shape),
            sparse_crow_indices=sparse_csr.crow_indices().tolist(),
            sparse_col_indices=sparse_csr.col_indices().tolist(),
        )

    # --- accessors ----------------------------------------------------------
    def to_numpy(self) -> npt.NDArray[Any]:
        if self.sparse_crow_indices is not None:
            return self.to_torch().numpy()
        return self._numpy

    def to_torch(self) -> "torch.Tensor":
        import torch

        torch_dtype = torch.int64 if self.dtype == "int64" else torch.float32
        if self.sparse_crow_indices is not None:
            assert self.sparse_col_indices is not None
            assert self.shape is not None
            crow = torch.tensor(self.sparse_crow_indices, dtype=torch.int64)
            col = torch.tensor(self.sparse_col_indices, dtype=torch.int64)
            values = torch.from_numpy(self._numpy).to(torch_dtype)
            return torch.sparse_csr_tensor(crow, col, values, self.shape).to_dense()
        t = torch.from_numpy(self._numpy)
        return t.to(torch_dtype) if t.dtype != torch_dtype else t

    @property
    def data(self) -> List[Any]:
        """The tensor's (dense) values as a plain Python list.

        The cookbook + battery read ``td.data`` directly — e.g.
        ``sum(weights.data)`` (whose result is then JSON-logged, so it must be a
        Python float, not numpy) and ``target_tokens.data[-1]`` in
        prompted_teacher. Returns Python-native values (reconstructed if sparse).
        """
        return self.to_numpy().tolist()

    def tolist(self) -> List[Any]:
        return self.to_numpy().tolist()
