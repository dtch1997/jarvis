"""Transformers-based sampler (no vLLM) — validates the eval-shim path on the pod.

A ``Sampler`` backed by HF ``generate`` + teacher-forced scoring, using the deps
already on the training pod (torch/transformers/peft). It's the single-pod M1
sampler; the vLLM worker (``sampler_worker.py``) is the perf backend for the
serverless split. Base model is loaded LAZILY on first use, and LoRA adapters
(named by ``weights_path``) are pulled from the blob store and hot-swapped.

``compute_logprobs`` returns the SDK convention: ``None`` at index 0 (no logprob
for the first token), then teacher-forced log p(token_i | tokens_<i>).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .blobstore import BlobStore
from .trainers.base import Sampler


class HFSampler(Sampler):
    def __init__(self, base_model: str, blob_root: Optional[str] = None):
        self.base_model = base_model
        self._blob = BlobStore(blob_root or "/mnt/volume")
        self._model = None
        self._tokenizer = None
        self._loaded_adapters: set[str] = set()
        self._device = None
        self._input_device = None

    # --- lazy load ----------------------------------------------------------
    def _ensure(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from .device_map import load_kwargs

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        device_count = torch.cuda.device_count() if self._device == "cuda" else 0
        dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
        kwargs = load_kwargs(dtype, device_count)
        self._sharded = "device_map" in kwargs  # >100B base split across GPUs
        self._tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        self._model = AutoModelForCausalLM.from_pretrained(self.base_model, **kwargs)
        # Sharded: accelerate placed each shard; a global .to() would undo it.
        if not self._sharded:
            self._model = self._model.to(self._device)
        # Inputs go to the embedding shard (== self._device when not sharded);
        # accelerate hooks route activations across shards from there.
        self._input_device = self._model.get_input_embeddings().weight.device
        self._model.eval()

    def _activate(self, weights_path: Optional[str]):
        """Select base (no adapter) or a LoRA adapter named by weights_path.

        Uses the transformers ``PeftAdapterMixin`` API consistently
        (load_adapter/set_adapter/enable_adapters on the base PreTrainedModel) —
        do NOT mix in ``PeftModel.from_pretrained``; the two adapter registries
        don't see each other.
        """
        self._ensure()
        if not weights_path:
            if getattr(self._model, "_hf_peft_config_loaded", False):
                self._model.disable_adapters()
            return
        local = str(self._blob.local_dir(weights_path))
        if weights_path not in self._loaded_adapters:
            self._model.load_adapter(local, adapter_name=weights_path)
            self._loaded_adapters.add(weights_path)
        self._model.set_adapter(weights_path)
        self._model.enable_adapters()

    # --- ops ----------------------------------------------------------------
    def sample(self, req: Dict[str, Any]) -> Dict[str, Any]:
        import torch

        self._activate(req.get("weights_path"))
        sp = req.get("sampling_params") or {}
        prompt_ids = req["prompt"]["tokens"]
        input_ids = torch.tensor([prompt_ids], device=self._input_device)
        max_new = sp.get("max_tokens") or 16
        temperature = sp.get("temperature", 1.0)
        do_sample = temperature and temperature > 0
        gen = self._model.generate(
            input_ids,
            max_new_tokens=max_new,
            do_sample=bool(do_sample),
            temperature=temperature if do_sample else None,
            top_p=sp.get("top_p", 1.0),
            top_k=(sp.get("top_k", -1) if sp.get("top_k", -1) and sp.get("top_k") > 0 else None),
            num_return_sequences=req.get("num_samples", 1),
            return_dict_in_generate=True,
            output_scores=True,
            pad_token_id=self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
        )
        seqs = gen.sequences[:, input_ids.shape[1]:]  # generated portion only
        # per-step chosen-token logprobs from scores
        logps = torch.stack(gen.scores, dim=1).log_softmax(-1)  # (n, T, V)
        sequences = []
        eos = self._tokenizer.eos_token_id
        for i in range(seqs.shape[0]):
            toks = seqs[i].tolist()
            lp = [float(logps[i, t, tok]) for t, tok in enumerate(toks)]
            # trim at eos
            stop = "length"
            if eos in toks:
                cut = toks.index(eos) + 1
                toks, lp, stop = toks[:cut], lp[:cut], "stop"
            sequences.append({"tokens": toks, "logprobs": lp, "stop_reason": stop})
        out: Dict[str, Any] = {"sequences": sequences}
        topk = int(req.get("topk_prompt_logprobs") or 0)
        if req.get("include_prompt_logprobs") or topk > 0:
            logp = self._prompt_logp(prompt_ids)  # one forward pass, reused below
            if req.get("include_prompt_logprobs"):
                out["prompt_logprobs"] = self._teacher_forced(prompt_ids, logp)
            if topk > 0:
                out["topk_prompt_logprobs"] = self._teacher_forced_topk(prompt_ids, topk, logp)
        return out

    def compute_logprobs(self, req: Dict[str, Any]) -> Dict[str, Any]:
        self._activate(req.get("weights_path"))
        prompt_ids = req["prompt"]["tokens"]
        return {"logprobs": self._teacher_forced(prompt_ids, self._prompt_logp(prompt_ids))}

    def _prompt_logp(self, prompt_ids: List[int]):
        """Teacher-forced ``(T, V)`` log-softmax over the prompt (one forward)."""
        import torch

        input_ids = torch.tensor([prompt_ids], device=self._input_device)
        with torch.no_grad():
            logits = self._model(input_ids).logits[0]  # (T, V)
        return logits.log_softmax(-1)

    def _teacher_forced(self, prompt_ids: List[int], logp) -> List[Optional[float]]:
        out: List[Optional[float]] = [None]  # index 0 undefined
        for i in range(1, len(prompt_ids)):
            out.append(float(logp[i - 1, prompt_ids[i]]))
        return out

    def _teacher_forced_topk(
        self, prompt_ids: List[int], k: int, logp
    ) -> List[Optional[List[tuple]]]:
        """Top-k ``(token_id, logprob)`` per prompt position; ``None`` at index 0.

        Position ``i`` predicts ``prompt_ids[i]`` from ``logp[i-1]`` (next-token
        distribution), matching the ``prompt_logprobs`` alignment. The cookbook's
        ``_collect_topk_for_datum`` reads these to build soft targets.
        """
        import torch

        out: List[Optional[List[tuple]]] = [None]  # index 0 undefined
        for i in range(1, len(prompt_ids)):
            vals, idx = torch.topk(logp[i - 1], k)
            out.append([(int(t), float(v)) for t, v in zip(idx.tolist(), vals.tolist())])
        return out


def make_hf_sampler(base_model: str, blob_root: Optional[str] = None) -> HFSampler:
    return HFSampler(base_model, blob_root)
