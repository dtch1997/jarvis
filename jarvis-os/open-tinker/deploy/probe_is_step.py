"""Real LoRATrainer importance_sampling forward/backward/optim step (issue #21, task 4).

Offline tests cover the pure loss fn + the FakeTrainer wire routing; this drives the
ACTUAL GPU LoRATrainer path on a tiny model through our backend:

  forward_backward("importance_sampling") -> optim_step  (x N steps)

With advantages = +1 everywhere, the surrogate -Σ adv·exp(logp_θ − samp_lp) is
minimized by RAISING logp_θ on the target tokens. So a correct gradient path must:
  (a) report a finite loss:sum and per-token logprobs,
  (b) produce grad_norm > 0 at optim_step (grads reach the LoRA adapters), and
  (c) make the mean target logprob INCREASE across steps (policy moves the right way).

Usage:  OPEN_TINKER_BASE_URL=... python deploy/probe_is_step.py [model]
"""

import json
import os
import sys

import open_tinker

open_tinker.use_as_tinker()

import tinker  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "OPEN_TINKER_TINY_MODEL", "Qwen/Qwen2.5-0.5B"
)
PROMPT = "The capital of France is Paris, a city known for its art and history."
STEPS = int(os.environ.get("PROBE_STEPS", "6"))
LR = float(os.environ.get("PROBE_LR", "1e-4"))

tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok.encode(PROMPT)
T = len(ids) - 1

sc = tinker.ServiceClient()
tc = sc.create_lora_training_client(base_model=MODEL, rank=16)


def make_datum():
    return tinker.types.Datum(
        model_input=tinker.types.ModelInput.from_ints(ids[:-1]),
        loss_fn_inputs={
            "target_tokens": ids[1:],
            "logprobs": [0.0] * T,        # fixed sampling logprobs
            "advantages": [1.0] * T,       # +1 everywhere -> raise target logp
        },
    )


def res(x):
    return x.result() if hasattr(x, "result") else x


steps = []
for s in range(STEPS):
    fb = res(tc.forward_backward([make_datum()], "importance_sampling"))
    rec = fb.loss_fn_outputs[0]
    lp = None
    for key in ("logprobs", "logprob", "token_logprobs"):
        if key in rec:
            lp = [float(v) for v in rec[key].data]
            break
    mean_lp = sum(lp) / len(lp) if lp else None
    os_resp = res(tc.optim_step(tinker.types.AdamParams(learning_rate=LR, grad_clip_norm=1.0)))
    gn = float(dict(getattr(os_resp, "metrics", {}) or {}).get("grad_norm", 0.0))
    steps.append(
        {
            "step": s,
            "loss_sum": round(float(dict(fb.metrics).get("loss:sum")), 5),
            "mean_target_logp": None if mean_lp is None else round(mean_lp, 5),
            "grad_norm": round(gn, 6),
        }
    )

out = {
    "model": MODEL,
    "n_tokens": T,
    "steps": steps,
    "mean_logp_increased": (
        steps[-1]["mean_target_logp"] > steps[0]["mean_target_logp"]
        if all(s["mean_target_logp"] is not None for s in steps)
        else None
    ),
    "all_grad_norms_positive": all(s["grad_norm"] > 0 for s in steps),
}
print("PROBE_IS_STEP_JSON " + json.dumps(out))
