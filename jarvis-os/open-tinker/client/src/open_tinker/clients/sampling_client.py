"""``SamplingClient`` — stateless generation/scoring given a weights handle.

Transport-agnostic: delegates to an injected
:class:`~open_tinker.protocol.Backend`. ``sample`` (rollouts / eval generation)
and ``compute_logprobs`` (teacher-forced per-token logprobs; ``None`` at the first
position, the convention ``battery``'s prompted-teacher ``[S+1:]`` re-alignment
relies on). Sampling is order-independent, so calls run on a shared thread pool
and return ``concurrent.futures.Future`` (matching the real SDK's ``sample``).
"""

from __future__ import annotations

from concurrent.futures import Future as ConcurrentFuture
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .. import types
from ..protocol import Backend

__all__ = ["SamplingClient"]

# Module-level pool shared across sampling clients; generation is stateless.
_POOL = ThreadPoolExecutor(max_workers=32, thread_name_prefix="ot-sample")


class SamplingClient:
    def __init__(self, backend: Backend, model: str, weights_path: Optional[str] = None):
        self._backend = backend
        self._model = model
        # Either a base-model name or a tinker://.../sampler_weights/... handle.
        self._weights_path = weights_path

    def sample(
        self,
        prompt: types.ModelInput,
        num_samples: int,
        sampling_params: types.SamplingParams,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
    ) -> "ConcurrentFuture[types.SampleResponse]":
        return _POOL.submit(
            self._backend.sample,
            self._model,
            self._weights_path,
            prompt,
            num_samples,
            sampling_params,
            include_prompt_logprobs,
            topk_prompt_logprobs,
        )

    async def sample_async(
        self,
        prompt: types.ModelInput,
        num_samples: int,
        sampling_params: types.SamplingParams,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
    ) -> types.SampleResponse:
        import asyncio

        fut = self.sample(
            prompt, num_samples, sampling_params, include_prompt_logprobs, topk_prompt_logprobs
        )
        return await asyncio.wrap_future(fut)

    def compute_logprobs(self, prompt: types.ModelInput) -> "ConcurrentFuture[List[float | None]]":
        return _POOL.submit(self._backend.compute_logprobs, self._model, self._weights_path, prompt)

    async def compute_logprobs_async(self, prompt: types.ModelInput) -> List[float | None]:
        import asyncio

        return await asyncio.wrap_future(self.compute_logprobs(prompt))

    def get_tokenizer(self):
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(self._model)

    def get_base_model(self) -> str:
        return self._model
