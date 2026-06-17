"""importance_sampling single-step parity probe (issue #21, task 2).

The on-policy reverse-KL distill loss has ONE open parity knob: the reduction
denominator (token-count vs masked-token vs sequence count) — isolated as `denom`
in server/.../trainers/lora.py. This probe runs a FIXED importance_sampling
forward_backward on a fresh rank-16 LoRA (lora_B=0 => base-model logits) against
one backend and dumps everything needed to *infer that backend's denominator*:

  loss:sum  = -Σ_t adv_t · exp(logp_θ(tok_t) − sampling_logprob_t)
  loss:mean = loss:sum / denom

So denom = loss:sum / loss:mean. We dump the reported metrics AND the per-token
logprobs the loss returns, so even if a backend doesn't report loss:sum we can
recompute it from (logprobs, advantages, sampling_logprobs) and divide.

Fixed batch (deterministic): advantages = 1.0 everywhere, sampling_logprobs = 0.0
everywhere. Then surrogate_t = exp(logp_θ(tok_t)); since both backends share the
base model (parity), loss:sum matches and only the denom can differ.

Usage:
    python deploy/parity_probe_is.py ours     # OPEN_TINKER_BASE_URL + open_tinker on path
    python deploy/parity_probe_is.py tinker    # TINKER_API_KEY (hosted)
"""

import json
import math
import os
import sys

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "ours"
N_DATA = int(sys.argv[2]) if len(sys.argv) > 2 else 1  # identical datums in the batch
# (disambiguates pure-sum vs per-sequence-mean: 2 copies double loss:sum iff sum.)

if BACKEND == "ours":
    import open_tinker

    open_tinker.use_as_tinker()

import tinker  # real (tinker) or shimmed (ours)  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
PROMPT = "The capital of France is Paris, a city known for its art and history."

tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok.encode(PROMPT)
T = len(ids) - 1  # one target per shifted position

sc = tinker.ServiceClient()
tc = sc.create_lora_training_client(base_model=MODEL, rank=16)

target = ids[1:]
sampling_logprobs = [0.0] * T
advantages = [1.0] * T

datum = tinker.types.Datum(
    model_input=tinker.types.ModelInput.from_ints(ids[:-1]),
    loss_fn_inputs={
        "target_tokens": target,
        "logprobs": sampling_logprobs,
        "advantages": advantages,
    },
)
fb = tc.forward_backward([datum] * N_DATA, "importance_sampling")
fb = fb.result() if hasattr(fb, "result") else fb

# pull per-token logprobs the loss returns (for recompute / cross-check)
returned_lp = None
try:
    rec = fb.loss_fn_outputs[0]
    for key in ("logprobs", "logprob", "token_logprobs"):
        if key in rec:
            returned_lp = [float(x) for x in rec[key].data]
            break
except Exception:  # noqa: BLE001
    pass

# recompute loss:sum from returned logprobs (independent of backend metric naming):
# loss_sum = -Σ adv · exp(logp − samp_lp)
recomputed_sum = None
if returned_lp is not None and len(returned_lp) == T:
    recomputed_sum = -sum(
        advantages[i] * math.exp(returned_lp[i] - sampling_logprobs[i]) for i in range(T)
    )

out = {
    "backend": BACKEND,
    "n_tokens": T,
    "metrics": dict(getattr(fb, "metrics", {}) or {}),
    "loss_fn_output_keys": list(fb.loss_fn_outputs[0].keys()) if fb.loss_fn_outputs else [],
    "returned_logprobs_head": None if returned_lp is None else [round(x, 5) for x in returned_lp[:8]],
    "recomputed_loss_sum": None if recomputed_sum is None else round(recomputed_sum, 6),
}

# infer the denominator from reported metrics if both sum & mean are present
m = out["metrics"]
ls = m.get("loss:sum")
lm = m.get("loss:mean")
if ls is not None and lm not in (None, 0):
    out["inferred_denom_from_metrics"] = round(float(ls) / float(lm), 4)
# also infer from recomputed sum vs reported mean (works even w/o reported loss:sum)
if recomputed_sum is not None and lm not in (None, 0):
    out["inferred_denom_from_recompute"] = round(recomputed_sum / float(lm), 4)

print("PARITY_IS_JSON " + json.dumps(out))
