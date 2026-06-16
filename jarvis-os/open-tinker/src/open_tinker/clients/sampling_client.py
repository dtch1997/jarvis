"""``SamplingClient`` — stateless generation/scoring given a weights handle.

Backed by serverless vLLM workers (spec §4.1 D, task #7). ``sample`` (rollouts /
eval generation) and ``compute_logprobs`` (teacher-forced per-token logprobs).
``compute_logprobs`` returns ``None`` where a logprob isn't defined (e.g. the
first token); ``battery``'s prompted-teacher ``[S+1:]`` re-alignment depends on
that. Sampling is order-independent, so calls run on a shared thread pool and
return ``concurrent.futures.Future`` (matching the real SDK's ``sample``).
"""

from __future__ import annotations

from concurrent.futures import Future as ConcurrentFuture
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .. import types
from .._serialize import decode_logprobs, decode_sample_response, encode_model_input
from .._transport import Transport

__all__ = ["SamplingClient"]

# Module-level pool shared across sampling clients; generation is stateless.
_POOL = ThreadPoolExecutor(max_workers=32, thread_name_prefix="ot-sample")


class SamplingClient:
    def __init__(self, transport: Transport, model: str, weights_path: Optional[str] = None):
        self._transport = transport
        self._model = model
        # Either a base-model name or a tinker://.../sampler_weights/... handle.
        self._weights_path = weights_path

    def _base_payload(self) -> dict:
        return {"model": self._model, "weights_path": self._weights_path}

    def sample(
        self,
        prompt: types.ModelInput,
        num_samples: int,
        sampling_params: types.SamplingParams,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
    ) -> "ConcurrentFuture[types.SampleResponse]":
        payload = {
            **self._base_payload(),
            "prompt": encode_model_input(prompt),
            "num_samples": num_samples,
            "sampling_params": sampling_params.model_dump(),
            "include_prompt_logprobs": include_prompt_logprobs,
            "topk_prompt_logprobs": topk_prompt_logprobs,
        }

        def _run():
            body = self._transport.request("sample", payload)
            return decode_sample_response(body)

        return _POOL.submit(_run)

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
        payload = {**self._base_payload(), "prompt": encode_model_input(prompt)}

        def _run():
            body = self._transport.request("logprobs", payload)
            return decode_logprobs(body)

        return _POOL.submit(_run)

    async def compute_logprobs_async(self, prompt: types.ModelInput) -> List[float | None]:
        import asyncio

        return await asyncio.wrap_future(self.compute_logprobs(prompt))

    def get_tokenizer(self):
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(self._model)

    def get_base_model(self) -> str:
        return self._model
