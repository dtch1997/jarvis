"""Hybrid-split (M3) end-to-end code-path validation on GPU (issue #21, task 6).

The hybrid split routes sampling through:

  control plane: RemoteVLLMSampler.sample(req)
      -> wrap {input: {**req, op: "sample"}}
      -> RunPod runsync  (HTTP — RunPod's infra)
  serverless worker: handler(job)
      -> VLLMEngine.sample(job["input"])   (real GPU vLLM)
      -> {output: <result>}
  control plane: unwrap {output} -> result

This drives EVERY hop that is OUR code against the LIVE vLLM engine, substituting an
in-process ``dispatch`` for the one hop that is RunPod's (the runsync HTTP call). The
dispatch returns the real RunPod runsync envelope ``{"status": "COMPLETED", "output":
...}`` so RemoteVLLMSampler._unwrap is exercised too. A full Docker build + serverless
endpoint is the only thing this can't cover on a box without Docker; the deploy recipe
is in deploy/runpod/PROVISIONING.md.

Usage:  OPEN_TINKER_BASE_MODEL=Qwen/Qwen2.5-0.5B python deploy/probe_hybrid_split.py
"""

import json
import os

from open_tinker_server.sampler_worker import RemoteVLLMSampler, handler

MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen2.5-0.5B")
PROMPT_TOKENS = [785, 6722, 315, 9625, 374]  # arbitrary fixed prompt ids


def runsync_sim(inp):
    """Stand in for the RunPod runsync HTTP call: run the real worker handler and
    wrap the output in RunPod's job envelope so _unwrap is exercised end-to-end."""
    out = handler({"input": inp})
    return {"id": "sim-job", "status": "COMPLETED", "output": out}


sampler = RemoteVLLMSampler(endpoint_id="local-sim", api_key="none", dispatch=runsync_sim)

sample_req = {
    "model": MODEL,
    "prompt": {"tokens": PROMPT_TOKENS},
    "num_samples": 2,
    "sampling_params": {"max_tokens": 8, "temperature": 0.7},
    "include_prompt_logprobs": True,
    "topk_prompt_logprobs": 5,
}
s = sampler.sample(sample_req)
lp = sampler.compute_logprobs({"model": MODEL, "prompt": {"tokens": PROMPT_TOKENS}})

result = {
    "model": MODEL,
    "sample_n_sequences": len(s.get("sequences", [])),
    "sample_seq0_len": len(s["sequences"][0]["tokens"]) if s.get("sequences") else 0,
    "prompt_logprobs_none_at_0": (s.get("prompt_logprobs") or [None])[0] is None,
    "topk_present": s.get("topk_prompt_logprobs") is not None,
    "topk_width_at_pos1": (
        len(s["topk_prompt_logprobs"][1]) if s.get("topk_prompt_logprobs") else 0
    ),
    "logprobs_none_at_0": (lp.get("logprobs") or [None])[0] is None,
    "logprobs_len": len(lp.get("logprobs") or []),
}
ok = (
    result["sample_n_sequences"] == 2
    and result["sample_seq0_len"] == 8
    and result["prompt_logprobs_none_at_0"]
    and result["topk_present"]
    and result["topk_width_at_pos1"] == 5
    and result["logprobs_none_at_0"]
    and result["logprobs_len"] == len(PROMPT_TOKENS)
)
result["HYBRID_SPLIT_OK"] = ok
print("PROBE_HYBRID_JSON " + json.dumps(result))
