"""Single-step numerical parity probe (task #8): our backend vs hosted Tinker.

Runs the SAME deterministic probe against one backend and emits JSON, so two runs
(ours / tinker) can be diffed. Two comparisons:

1. compute_logprobs on the BASE model over a fixed prompt — the cleanest
   apples-to-apples (no LoRA, so no init differences). Same base model => the
   per-token logprobs should match closely (modulo inference-kernel/precision).
2. forward_backward(cross_entropy) on a fixed batch with a FRESH rank-16 LoRA.
   peft/Tinker both init lora_B=0, so the adapter contributes nothing at step 0
   => the loss is the base model's loss, again comparable.

Usage:
    python deploy/parity_probe.py ours    # needs OPEN_TINKER_BASE_URL + open_tinker on path
    python deploy/parity_probe.py tinker   # needs TINKER_API_KEY (hosted)
"""

import json
import os
import sys

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "ours"
# which test(s) to run: "logprobs" | "fb" | "both". On our single 80GB pod the
# sampler and trainer each load a full 27B copy, so run them in separate server
# lifetimes (hosted Tinker has no such constraint -> "both").
WHICH = sys.argv[2] if len(sys.argv) > 2 else "both"

if BACKEND == "ours":
    import open_tinker

    open_tinker.use_as_tinker()

import tinker  # real (tinker) or shimmed (ours)  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")
PROMPT = "The capital of France is Paris, a city known for its art and history."

tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok.encode(PROMPT)

sc = tinker.ServiceClient()

out = {"backend": BACKEND, "which": WHICH, "n_tokens": len(ids), "ids_head": ids[:8]}

# --- 1. base-model compute_logprobs ----------------------------------------
if WHICH in ("logprobs", "both"):
    samp = sc.create_sampling_client(base_model=MODEL)
    lp = samp.compute_logprobs(tinker.types.ModelInput.from_ints(ids))
    lp = lp.result() if hasattr(lp, "result") else lp
    out["compute_logprobs"] = [None if x is None else round(float(x), 5) for x in lp]

# --- 2. forward_backward on a fresh LoRA ------------------------------------
if WHICH in ("fb", "both"):
    tc = sc.create_lora_training_client(base_model=MODEL, rank=16)
    datum = tinker.types.Datum(
        model_input=tinker.types.ModelInput.from_ints(ids[:-1]),
        loss_fn_inputs={"target_tokens": ids[1:], "weights": [1.0] * (len(ids) - 1)},
    )
    fb = tc.forward_backward([datum], "cross_entropy")
    fb = fb.result() if hasattr(fb, "result") else fb
    sum_logprobs = None
    try:
        rec = fb.loss_fn_outputs[0]
        for key in ("logprobs", "logprob", "token_logprobs"):
            if key in rec:
                sum_logprobs = float(sum(rec[key].data))
                break
    except Exception:  # noqa: BLE001
        pass
    out["fb_metrics"] = dict(getattr(fb, "metrics", {}) or {})
    out["fb_loss_fn_output_keys"] = list(fb.loss_fn_outputs[0].keys()) if fb.loss_fn_outputs else []
    out["fb_sum_logprobs"] = None if sum_logprobs is None else round(sum_logprobs, 5)

print("PARITY_JSON " + json.dumps(out))
