"""Direct vLLM-engine topk dump for parity vs hosted Tinker (issue #50, item 1).

The hosted side runs ``parity_probe_topk.py tinker``; this is the matching
``ours`` side, but it drives ``VLLMEngine`` (our real vLLM code path:
``sample(topk_prompt_logprobs=k)`` -> ``_topk_prompt_logprobs``) IN-PROCESS on a
GPU box, rather than over the HTTP control plane (M1-validated, orthogonal to
topk correctness). Same fixed prompt, same ``k``, same normalization as
``parity_probe_topk.py`` so the two outputs diff cleanly with ``topk_compare.py``.

The 27B (Qwen3.6, ``Qwen3_5ForConditionalGeneration``) is not yet supported by any
released vLLM, so parity is run on a substitute model that BOTH hosted Tinker and
the vLLM engine support (default ``Qwen/Qwen3-8B``, ``Qwen3ForCausalLM``).

Usage:  OPEN_TINKER_BASE_MODEL=Qwen/Qwen3-8B python deploy/probe_topk_local.py [k]
"""

import json
import os
import sys

from transformers import AutoTokenizer

from open_tinker_server.sampler_worker import VLLMEngine

K = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3-8B")
PROMPT = "The capital of France is Paris, a city known for its art and history."

tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok.encode(PROMPT)

engine = VLLMEngine(base_model=MODEL)
resp = engine.sample(
    {
        "model": MODEL,
        "prompt": {"tokens": ids},
        "num_samples": 1,
        "sampling_params": {"max_tokens": 1},
        "include_prompt_logprobs": True,
        "topk_prompt_logprobs": K,
    }
)
topk = resp.get("topk_prompt_logprobs")


def norm(entry):
    if entry is None:
        return None
    out = {}
    for pair in entry:
        t, lp = int(pair[0]), float(pair[1])
        out[t] = round(lp, 5)
    return out


positions = [norm(e) for e in (topk or [])]
out = {
    "backend": "ours",
    "k": K,
    "n_tokens": len(ids),
    "n_positions": len(positions),
    "positions": positions,
}
print("PARITY_TOPK_JSON " + json.dumps(out))
