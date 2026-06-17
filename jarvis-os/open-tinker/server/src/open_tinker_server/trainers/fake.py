"""CPU, dependency-free backends for integration tests / CI.

``FakeTrainer`` / ``FakeSampler`` implement the ``Trainer`` / ``Sampler``
interfaces with trivial-but-faithful behavior (track accumulation, emit the wire
shapes, honor the prompt-logprobs None-at-0 convention). They let the FastAPI
control plane be tested over a real ASGI/HTTP path without torch/peft/vllm. They
mirror the ReferenceBackend in the client's test suite — keep the two in sync.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from open_tinker._serialize import encode_tensor
from open_tinker.types import Datum, TensorData

from .base import Sampler, Trainer


class FakeTrainer(Trainer):
    def __init__(self, run_id: str, body: Dict[str, Any], store):
        self.run_id = run_id
        self.base_model = body.get("base_model") or "resumed-base"
        self._store = store
        self.fwdbwd_calls = 0
        self.steps = 0
        self.closed = False

    def forward_backward(
        self, data: List[Datum], loss_fn: str, loss_fn_config: Dict[str, float] | None
    ) -> Dict[str, Any]:
        self.fwdbwd_calls += 1
        outs = []
        for d in data:
            n = d.model_input.length
            outs.append({"logprobs": encode_tensor(TensorData.from_numpy(np.zeros(n, np.float32)))})
        return {
            "loss_fn_output_type": "ArrayRecord",
            "loss_fn_outputs": outs,
            "metrics": {"loss:sum": float(len(data)), "loss:mean": 1.0},
        }

    def optim_step(self, adam_params: Dict[str, float]) -> Dict[str, Any]:
        self.steps += 1
        consumed = self.fwdbwd_calls
        self.fwdbwd_calls = 0
        return {"metrics": {"grad_norm": 0.0, "microbatches": float(consumed)}}

    def save(self, kind: str, name: str, ttl_seconds: int | None, overwrite: bool) -> str:
        path = self._store.make_path(self.run_id, kind, name)
        self._store.local_dir(path, create=True)
        return path

    def load_state(self, path: str) -> None:
        return None

    def close(self) -> None:
        # No VRAM to free (CPU fake); record it so eviction is observable in tests.
        self.closed = True


def make_fake_trainer(run_id: str, body: Dict[str, Any], store) -> FakeTrainer:
    return FakeTrainer(run_id, body, store)


class FakeSampler(Sampler):
    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        toks = req["prompt"]["tokens"]
        n = req["num_samples"]
        max_tokens = (req.get("sampling_params") or {}).get("max_tokens") or 3
        seqs = [
            {"tokens": list(range(max_tokens)), "logprobs": [-0.1] * max_tokens, "stop_reason": "length"}
            for _ in range(n)
        ]
        out: Dict[str, Any] = {"sequences": seqs}
        if req.get("include_prompt_logprobs"):
            out["prompt_logprobs"] = [None] + [-0.5] * (len(toks) - 1)
        topk = int(req.get("topk_prompt_logprobs") or 0)
        if topk > 0:
            # One entry per prompt token (None at index 0); k descending pairs.
            out["topk_prompt_logprobs"] = [None] + [
                [(t, -0.5 - 0.1 * j) for j, t in enumerate(range(topk))]
                for _ in range(len(toks) - 1)
            ]
        return out

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        toks = req["prompt"]["tokens"]
        return {"logprobs": [None] + [-0.3] * (len(toks) - 1)}
