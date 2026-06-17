"""Checkpoint types + the ``tinker://`` path grammar.

``tinker://<run_id>/weights/<id>``           → full training state (resumable)
``tinker://<run_id>/sampler_weights/<id>``   → inference-only adapter weights

Our control plane resolves these to blob-store keys (spec §4.1/§5). The grammar
here matches the real SDK so any path battery persists/loads round-trips.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from typing_extensions import Literal, TypeAlias

__all__ = ["Checkpoint", "CheckpointType", "ParsedCheckpointTinkerPath", "ModelID"]

ModelID: TypeAlias = str
CheckpointType = Literal["training", "sampler"]


class Checkpoint(BaseModel):
    checkpoint_id: str
    checkpoint_type: CheckpointType
    time: datetime
    tinker_path: str
    size_bytes: Optional[int] = None
    public: bool = False
    expires_at: Optional[datetime] = None


class ParsedCheckpointTinkerPath(BaseModel):
    tinker_path: str
    training_run_id: str
    checkpoint_type: CheckpointType
    checkpoint_id: str

    @classmethod
    def from_tinker_path(cls, tinker_path: str) -> "ParsedCheckpointTinkerPath":
        if not tinker_path.startswith("tinker://"):
            raise ValueError(f"Invalid tinker path: {tinker_path}")
        parts = tinker_path[len("tinker://"):].split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid tinker path: {tinker_path}")
        if parts[1] not in ("weights", "sampler_weights"):
            raise ValueError(f"Invalid tinker path: {tinker_path}")
        checkpoint_type: CheckpointType = "training" if parts[1] == "weights" else "sampler"
        return cls(
            tinker_path=tinker_path,
            training_run_id=parts[0],
            checkpoint_type=checkpoint_type,
            checkpoint_id="/".join(parts[1:]),
        )
