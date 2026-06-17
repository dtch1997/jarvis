"""Multi-GPU model sharding config — turn env into HF ``from_pretrained`` kwargs.

The training/sampling engines load a *whole* base model onto one device
(``.to(device)``), which caps the servable model at what fits a single GPU
(validated up to 27B on one H100). To finetune models that don't fit one GPU
(>100B), transformers/accelerate can shard the layers across every visible GPU
via ``device_map`` (naive pipeline parallelism: layer N on GPU ``f(N)``, activations
hop devices through accelerate hooks). PEFT trains LoRA adapters on top of such a
dispatched base unchanged — the adapters live on their parent module's shard and
the optimizer just collects ``requires_grad`` params across devices.

This module is the ONE place that decides whether/how to shard, driven by env so
it's a deploy choice (like ``OPEN_TINKER_BASE_MODEL``). It's pure (env-string in,
kwargs out) so the policy is unit-testable on CPU without torch.

Knobs
-----
``OPEN_TINKER_DEVICE_MAP``
    Unset (default): shard with ``"auto"`` iff >1 GPU is visible, else load
    single-device (the validated, bit-identical path). Explicit values:
    ``"auto"`` / ``"balanced"`` / ``"balanced_low_0"`` / ``"sequential"`` force an
    accelerate strategy; a JSON object is a literal module→device map; and
    ``"single"`` / ``"off"`` / ``"none"`` / ``"0"`` force the single-device path
    even on a multi-GPU box.
``OPEN_TINKER_MAX_MEMORY``
    Optional JSON cap per device, e.g. ``{"0":"70GiB","1":"70GiB","cpu":"200GiB"}``
    (int-like keys → GPU indices). Forwarded to accelerate as ``max_memory`` to
    leave headroom for activations + LoRA/optimizer state, or to force a split
    onto N GPUs in a smoke test. Ignored when loading single-device.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Union

DeviceMap = Union[str, Dict[str, Any]]

# Distinct from None so callers can pass env=None to mean "no env var set".
_READ_ENV = object()

_SINGLE_ALIASES = {"", "single", "off", "none", "no", "0", "false"}


def resolve_device_map(device_count: int, env: Any = _READ_ENV) -> Optional[DeviceMap]:
    """Decide the ``device_map`` to load with, or ``None`` for single-device.

    ``device_count`` is the number of visible CUDA devices. ``env`` defaults to
    reading ``OPEN_TINKER_DEVICE_MAP``; pass it explicitly (incl. ``None``) in tests.
    """
    if env is _READ_ENV:
        env = os.environ.get("OPEN_TINKER_DEVICE_MAP")
    if env is None:
        # No explicit choice: shard only when there's more than one GPU to shard
        # onto; otherwise keep the single-device path (unchanged behavior).
        return "auto" if device_count > 1 else None
    val = env.strip()
    if val.lower() in _SINGLE_ALIASES:
        return None
    if val.startswith("{"):  # literal module->device map
        return json.loads(val)
    return val  # an accelerate strategy string ("auto", "balanced", ...)


def resolve_max_memory(env: Any = _READ_ENV) -> Optional[Dict[Any, str]]:
    """Parse ``OPEN_TINKER_MAX_MEMORY`` JSON into accelerate's ``max_memory`` dict.

    Int-like keys become ``int`` GPU indices (accelerate's expected type); ``"cpu"``
    / ``"disk"`` pass through. Returns ``None`` when unset.
    """
    if env is _READ_ENV:
        env = os.environ.get("OPEN_TINKER_MAX_MEMORY")
    if not env:
        return None
    raw = json.loads(env)
    out: Dict[Any, str] = {}
    for k, v in raw.items():
        out[int(k) if str(k).isdigit() else k] = v
    return out


def load_kwargs(torch_dtype, device_count: int) -> Dict[str, Any]:
    """Build the ``from_pretrained`` kwargs (dtype + optional sharding).

    Returns ``{"torch_dtype": ...}`` plus ``device_map`` (and ``max_memory`` when
    given) when sharding is in effect. When ``device_map`` is absent the caller is
    responsible for the single-device ``.to(device)`` move, preserving the
    validated single-GPU path exactly.
    """
    kwargs: Dict[str, Any] = {"torch_dtype": torch_dtype}
    device_map = resolve_device_map(device_count)
    if device_map is not None:
        kwargs["device_map"] = device_map
        max_memory = resolve_max_memory()
        if max_memory is not None:
            kwargs["max_memory"] = max_memory
    return kwargs
