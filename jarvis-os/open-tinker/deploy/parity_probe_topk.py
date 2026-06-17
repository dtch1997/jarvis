"""topk_prompt_logprobs parity probe (issue #21, task 3).

Off-policy forward-KL soft targets come from ``sample(topk_prompt_logprobs=k)``
(the teacher's top-k next-token distribution at each prompt position). The pure
decode is unit-tested, but the vLLM engine path is GPU-only. This probe runs the
EXACT call ``train_off_policy._collect_topk_for_datum`` makes against one backend
and dumps the top-k (token_id, logprob) pairs per position, so two runs (ours via
the live vLLM sampler / tinker hosted) can be diffed for set overlap + logprob Δ.

Usage:
    python deploy/parity_probe_topk.py ours      # OPEN_TINKER_BASE_URL + open_tinker on path
    python deploy/parity_probe_topk.py tinker     # TINKER_API_KEY (hosted)
"""

import asyncio
import json
import os
import sys

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "ours"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 20

if BACKEND == "ours":
    import open_tinker

    open_tinker.use_as_tinker()

import tinker  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
PROMPT = "The capital of France is Paris, a city known for its art and history."

tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok.encode(PROMPT)

sc = tinker.ServiceClient()
samp = sc.create_sampling_client(base_model=MODEL)


async def go():
    resp = await samp.sample_async(
        prompt=tinker.types.ModelInput.from_ints(ids),
        num_samples=1,
        sampling_params=tinker.types.SamplingParams(max_tokens=1),
        include_prompt_logprobs=True,
        topk_prompt_logprobs=K,
    )
    return resp


resp = asyncio.run(go())
topk = resp.topk_prompt_logprobs

# Normalize to [ {tok: lp, ...} per position ] (None at 0). Each entry is a list of
# (token_id, logprob) pairs (our shape) or possibly objects — handle both.
def norm(entry):
    if entry is None:
        return None
    out = {}
    for pair in entry:
        if isinstance(pair, (list, tuple)):
            t, lp = int(pair[0]), float(pair[1])
        else:  # object with .token/.logprob style
            t, lp = int(getattr(pair, "token", getattr(pair, "token_id", None))), float(pair.logprob)
        out[t] = round(lp, 5)
    return out


positions = [norm(e) for e in (topk or [])]
out = {
    "backend": BACKEND,
    "k": K,
    "n_tokens": len(ids),
    "n_positions": len(positions),
    "positions": positions,  # [None, {tok:lp,...}, ...]
}
print("PARITY_TOPK_JSON " + json.dumps(out))
