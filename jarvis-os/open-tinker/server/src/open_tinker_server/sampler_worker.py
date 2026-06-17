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
        import os

        # Run the vLLM V1 engine IN-PROCESS (no forked EngineCore). When the sampler is
        # co-located with anything that has already touched CUDA — the control plane
        # (it imports torch), or a warm serverless worker — vLLM's default forked
        # EngineCore dies with "Cannot re-initialize CUDA in forked subprocess"
        # (issue #21 task 3, only reproducible on GPU). In-process is also what the
        # single-pod M1 topology wants. setdefault so an operator can still override.
        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
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
        topk = int(req.get("topk_prompt_logprobs") or 0)
        # vLLM's prompt_logprobs=k returns the top-k logprobs per prompt position
        # (k>0 also covers the chosen-token lookup _prompt_logprobs needs).
        if topk > 0:
            prompt_lp = topk
        elif req.get("include_prompt_logprobs"):
            prompt_lp = 0
        else:
            prompt_lp = None
        params = VSamplingParams(
            n=req["num_samples"],
            max_tokens=sp.get("max_tokens") or 16,
            temperature=sp.get("temperature", 1.0),
            top_p=sp.get("top_p", 1.0),
            top_k=sp.get("top_k", -1),
            seed=sp.get("seed"),
            stop_token_ids=None,
            prompt_logprobs=prompt_lp,
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
        if topk > 0:
            resp["topk_prompt_logprobs"] = _topk_prompt_logprobs(out, topk)
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


def _topk_prompt_logprobs(out, k: int) -> List[Optional[List[tuple]]]:
    """vLLM prompt_logprobs(k) -> ``[None, [(tok, lp), ..], ..]`` (None at index 0).

    Each ``out.prompt_logprobs[i]`` is a ``{token_id: Logprob}`` map of the top
    entries at position ``i``; we sort by logprob desc and keep the top ``k`` as
    ``(token_id, logprob)`` tuples — the shape ``train_off_policy`` expects from
    ``SampleResponse.topk_prompt_logprobs``.
    """
    result: List[Optional[List[tuple]]] = []
    for i, entry in enumerate(out.prompt_logprobs or []):
        if entry is None or i == 0:
            result.append(None)
        else:
            pairs = sorted(
                ((tok, lp.logprob) for tok, lp in entry.items()),
                key=lambda p: p[1],
                reverse=True,
            )[:k]
            result.append([(int(tok), float(lp)) for tok, lp in pairs])
    return result


class LocalVLLMSampler(Sampler):
    """In-process sampler for the single-pod M1 deployment."""

    def __init__(self, base_model: str, blob_root: Optional[str] = None):
        self._engine = VLLMEngine(base_model, blob_root)

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._engine.sample(req)

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._engine.compute_logprobs(req)


class RemoteSamplerError(RuntimeError):
    """A serverless sampling job did not complete successfully."""


class RemoteVLLMSampler(Sampler):
    """Control-plane → serverless dispatch for the hybrid split (M3).

    In the hybrid topology (spec §4.2) the always-on control plane does NOT hold a
    GPU; it forwards ``sample`` / ``compute_logprobs`` to the autoscaled RunPod
    serverless endpoint running :func:`handler`. This is the glue that calls that
    endpoint's ``runsync`` route, wrapping the wire body as ``{"input": {...,
    "op": "sample"|"logprobs"}}`` and unwrapping the ``{"output": ...}`` envelope.

    ``Sampler``-conformant, so it drops into ``create_app(sampler=...)`` exactly
    where ``LocalVLLMSampler`` / ``HFSampler`` go — the control plane is then a
    CPU-only box that owns no model. The HTTP POST is injectable (``dispatch``)
    so the routing is unit-testable without RunPod or a network; the default uses
    ``httpx`` (a client dep, always present) against the RunPod v2 API.
    """

    def __init__(
        self,
        endpoint_id: str,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 600.0,
        dispatch: Optional[Any] = None,
    ):
        import os

        self._endpoint_id = endpoint_id
        self._api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        self._base_url = (
            base_url or os.environ.get("RUNPOD_ENDPOINT_BASE_URL", "https://api.runpod.ai/v2")
        ).rstrip("/")
        self._timeout = timeout
        # dispatch(input_dict) -> raw runsync JSON. Default: real RunPod POST.
        self._dispatch = dispatch or self._runsync

    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._run({**req, "op": "sample"})

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self._run({**req, "op": "logprobs"})

    def _run(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        return self._unwrap(self._dispatch(inp))

    @staticmethod
    def _unwrap(result: Any) -> Dict[str, Any]:
        """RunPod runsync envelope → the handler's output dict (or raise).

        ``runsync`` returns ``{"id", "status", "output"}``. We surface ``output``
        on ``COMPLETED`` and raise on any failed/non-terminal status. A bare dict
        with no ``status`` (e.g. an injected test dispatcher) is treated as the
        output directly.
        """
        if not isinstance(result, dict):
            raise RemoteSamplerError(f"serverless response was {type(result).__name__}, not a dict")
        status = result.get("status")
        if status is None:
            return result
        if status != "COMPLETED":
            raise RemoteSamplerError(
                f"serverless job status={status!r}: {result.get('error') or result}"
            )
        if "output" not in result:
            raise RemoteSamplerError(f"serverless job COMPLETED but had no 'output': {result}")
        return result["output"]

    def _runsync(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        import httpx

        url = f"{self._base_url}/{self._endpoint_id}/runsync"
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        resp = httpx.post(url, json={"input": inp}, headers=headers, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()


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
