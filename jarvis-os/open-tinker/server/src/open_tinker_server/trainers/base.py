"""Backend engine interfaces the control plane routes to.

``Trainer`` (one stateful training session per ``model_id``) and ``Sampler``
(stateless generation/scoring) are now defined ONCE in the light client package
(``open_tinker.protocol``) so the client's ``LocalBackend`` and the server's
concrete engines (``LoRATrainer`` / ``HFSampler`` / vLLM) share a single,
type-checked contract. This module just re-exports them.

Trainers receive already-decoded ``Datum`` objects and return the wire dicts the
control plane forwards (WIRE_PROTOCOL.md).
"""

from __future__ import annotations

from open_tinker.protocol import Sampler, Trainer

__all__ = ["Trainer", "Sampler"]
