"""Request parameter types: ``AdamParams``, ``SamplingParams``, ``LoraConfig``.

Defaults match the real ``tinker.types`` exactly (e.g. Adam ``beta2=0.95``,
``eps=1e-12``) — the backend optimizer must honor these for numerical parity
(spec §8).
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

from pydantic import BaseModel

__all__ = ["AdamParams", "SamplingParams", "LoraConfig"]


class AdamParams(BaseModel):
    learning_rate: float = 0.0001
    beta1: float = 0.9
    beta2: float = 0.95
    eps: float = 1e-12
    weight_decay: float = 0.0
    # Max global grad norm; 0.0 == no clipping (decoupled weight decay, per SDK).
    grad_clip_norm: float = 0.0


class SamplingParams(BaseModel):
    max_tokens: Optional[int] = None
    seed: Optional[int] = None
    stop: Union[str, Sequence[str], Sequence[int], None] = None
    temperature: float = 1.0
    top_k: int = -1
    top_p: float = 1.0


class LoraConfig(BaseModel):
    rank: int
    seed: Optional[int] = None
    train_unembed: bool = True
    train_mlp: bool = True
    train_attn: bool = True
