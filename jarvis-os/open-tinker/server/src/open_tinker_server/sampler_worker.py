"""vLLM sampling/scoring (spec §4.1 D, task #7).

Two deployment shapes share one core (``VLLMEngine``):

- ``LocalVLLMSampler`` — in-process ``Sampler`` for the single-pod M1 deployment
  (the control plane calls it directly).
- ``handler(job)`` — a RunPod **serverless** entrypoint for the hybrid split,
  where the control plane's ``RemoteVLLMSampler`` dispatches sample/logprobs to
  autoscaled workers. Same request/response bodies as WIRE_PROTOCOL.md.

``vllm`` is imported lazily (``[sample]`` extra); the adapter named by
``weights_path`` is pulled from the blob store (Network Volume) and hot-loaded.
``compute_logprobs`` returns the SDK convention: ``None`` at index 0.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .trainers.base import Sampler


class VLLMEngine:
    """Thin wrapper over a vLLM engine with LoRA hot-load. GPU-only."""

    def __init__(self, base_model: str, blob_root: Optional[str] = None, max_loras: int = 8):
        from vllm import LLM  # lazy

        self.base_model = base_model
        self.blob_root = blob_root
        self._llm = LLM(model=base_model, enable_lora=True, max_loras=max_loras)
        self._lora_cache: Dict[str, Any] = {}

    def _lora_request(self, weights_path: Optional[str]):
        if not weights_path:
            return None
        from vllm.lora.request import LoRARequest

        from .blobstore import BlobStore

        if weights_path not in self._lora_cache:
            local = BlobStore(self.blob_root or "/mnt/volume").local_dir(weights_path)
            idx = len(self._lora_cache) + 1
            self._lora_cache[weights_path] = LoRARequest(f"lora{idx}", idx, str(local))
        return self._lora_cache[weights_path]

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        from vllm import SamplingParams as VSamplingParams

        sp = req.get("sampling_params") or {}
        params = VSamplingParams(
            n=req["num_samples"],
            max_tokens=sp.get("max_tokens") or 16,
            temperature=sp.get("temperature", 1.0),
            top_p=sp.get("top_p", 1.0),
            top_k=sp.get("top_k", -1),
            seed=sp.get("seed"),
            stop_token_ids=None,
            prompt_logprobs=0 if req.get("include_prompt_logprobs") else None,
            logprobs=0,
        )
        out = self._llm.generate(
            prompt_token_ids=[req["prompt"]["tokens"]],
            sampling_params=params,
            lora_request=self._lora_request(req.get("weights_path")),
        )[0]
        sequences = []
        for o in out.outputs:
            lps = [list(lp.values())[0].logprob for lp in (o.logprobs or [])] if o.logprobs else None
            sequences.append(
                {
                    "tokens": list(o.token_ids),
                    "logprobs": lps,
                    "stop_reason": "stop" if o.finish_reason == "stop" else "length",
                }
            )
        resp: Dict[str, Any] = {"sequences": sequences}
        if req.get("include_prompt_logprobs"):
            resp["prompt_logprobs"] = _prompt_logprobs(out)
        return resp

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Teacher-forced per-token logprobs over the prompt (vLLM prompt_logprobs)."""
        from vllm import SamplingParams as VSamplingParams

        params = VSamplingParams(max_tokens=1, temperature=0.0, prompt_logprobs=0)
        out = self._llm.generate(
            prompt_token_ids=[req["prompt"]["tokens"]],
            sampling_params=params,
            lora_request=self._lora_request(req.get("weights_path")),
        )[0]
        return {"logprobs": _prompt_logprobs(out)}


def _prompt_logprobs(out) -> List[Optional[float]]:
    """vLLM prompt_logprobs -> [None, lp1, lp2, ...] (None at index 0)."""
    result: List[Optional[float]] = []
    for i, entry in enumerate(out.prompt_logprobs or []):
        if entry is None or i == 0:
            result.append(None)
        else:
            tok_id = out.prompt_token_ids[i]
            lp = entry.get(tok_id)
            result.append(lp.logprob if lp is not None else None)
    return result


class LocalVLLMSampler(Sampler):
    """In-process sampler for the single-pod M1 deployment."""

    def __init__(self, base_model: str, blob_root: Optional[str] = None):
        self._engine = VLLMEngine(base_model, blob_root)

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._engine.sample(req)

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._engine.compute_logprobs(req)


class RemoteVLLMSampler(Sampler):
    """Control-plane → serverless dispatch for the hybrid split (M3, planned).

    In the hybrid topology (spec §4.2) the always-on control plane does NOT hold
    a GPU; it forwards sample/logprobs requests to the autoscaled RunPod
    serverless endpoint running ``handler`` below. This is the glue that calls
    that endpoint (``runsync``) — implement when splitting sampling off the
    training pod. Until then the single-pod deployments use ``LocalVLLMSampler``
    or ``HFSampler``.
    """

    def __init__(self, endpoint_id: str, api_key: Optional[str] = None):
        self._endpoint_id = endpoint_id
        self._api_key = api_key

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "RemoteVLLMSampler.sample (serverless dispatch, M3 hybrid split) is not implemented yet."
        )

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "RemoteVLLMSampler.compute_logprobs (serverless dispatch, M3) is not implemented yet."
        )


# --- RunPod serverless entrypoint (hybrid split) ---------------------------
_ENGINE: Optional[VLLMEngine] = None


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """RunPod serverless handler. ``job['input'] = {op, ...wire body...}``."""
    global _ENGINE
    import os

    inp = job["input"]
    if _ENGINE is None:
        _ENGINE = VLLMEngine(
            base_model=inp.get("model") or os.environ["OPEN_TINKER_BASE_MODEL"],
            blob_root=os.environ.get("OPEN_TINKER_BLOB_ROOT", "/runpod-volume"),
        )
    op = inp.get("op", "sample")
    if op == "sample":
        return _ENGINE.sample(inp)
    if op == "logprobs":
        return _ENGINE.compute_logprobs(inp)
    raise ValueError(f"unknown op {op!r}")


def main() -> None:
    import runpod  # type: ignore

    runpod.serverless.start({"handler": handler})


if __name__ == "__main__":
    main()
