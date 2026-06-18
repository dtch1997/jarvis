# Modal backend — live GPU runs (#31)

Live results for the two GPU-gated #31 follow-ups, run on the Modal backend
(`deploy/modal/app.py`) in the `arcadia-alignment-team` workspace, 2026-06-17.
Both depend on PR #51 (the `OPEN_TINKER_SAMPLER_BACKEND` toggle + vLLM image) and
the vllm/transformers pin (this branch).

---

## 1. vLLM sampler throughput + burst right-sizing (Qwen3-8B)

**What & why.** Exercises the `OPEN_TINKER_SAMPLER_BACKEND=vllm` path end-to-end on
Modal (the #51 toggle, on the pinned vLLM-0.11 image) and drives `deploy/fanout_demo.py`
at the **deployed** `/v1/logprobs` to size `OPEN_TINKER_MODAL_MIN_SAMPLERS`. 8B
(`Qwen3ForCausalLM`), not 27B, because no released vLLM serves 27B's `Qwen3_5*` arch
(see §2 / #53).

**Deploy:**
```bash
OPEN_TINKER_BASE_MODEL=Qwen/Qwen3-8B OPEN_TINKER_SAMPLER_BACKEND=vllm \
  modal run  open-tinker/deploy/modal/app.py::provision      # cache 8B weights
OPEN_TINKER_BASE_MODEL=Qwen/Qwen3-8B OPEN_TINKER_SAMPLER_BACKEND=vllm \
OPEN_TINKER_MODAL_GPU=H100 OPEN_TINKER_MODAL_MIN_SAMPLERS=0 OPEN_TINKER_MODAL_MAX_SAMPLERS=4 \
  modal deploy open-tinker/deploy/modal/app.py
```

**First-load (pin) validation.** The single cold request below loaded vLLM 0.11.0 +
transformers 4.57.1 and scored a prompt with **no** `Qwen2Tokenizer` /
`all_special_tokens_extended` crash — i.e. the pin recipe from #53 works on Modal, and
the #51 toggle serves real vLLM. (The previous bare-`vllm` image would have failed here.)

**Results** (`compute_logprobs`, 8-token prompt, H100 sampler, `max_inputs=4`):

| run | n | concurrency | warm samplers | ok | wall | p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| cold single | 1 | 1 | 0 (scale-to-zero) | 1/1 | 32.5s | — | — | **32.5s** |
| warm burst | 32 | 16 | 1 | 32/32 | 9.4s (3.4 req/s) | 4.33s | 4.93s | 5.51s |

**Reading it / right-sizing `OPEN_TINKER_MODAL_MIN_SAMPLERS`:**
- A **cold** sampler pays ~**32s** to boot vLLM + load 8B — this is the entire tail.
- **One** warm container then absorbs a **16-wide** burst at **p95 ≈ 5s, 0 failures**:
  `@modal.concurrent(max_inputs=4)` batches 4 in-flight, so 32 requests drain in ~9s
  before any *additional* cold container would have finished booting.
- ⇒ **`MIN_SAMPLERS=1` is enough** for interactive/bursty `logprobs` on an 8B-class
  model — it converts the first-request 32s → ~5s. Raise it further only if sustained
  concurrency exceeds what one container's batching holds under your latency SLO;
  `MAX_SAMPLERS` still absorbs spikes above the warm pool (at cold-start latency).

---

## 2. 27B / H100 parity on the Modal backend — HF sampler

**What & why.** The Modal analogue of `deploy/runpod/PARITY_RESULT.md`: confirm the HF
sampler + LoRA trainer produce hosted-Tinker-equivalent numbers for the 27B base
(`Qwen/Qwen3.6-27B`) on Modal's H100s. Two comparisons (same as `parity_probe.py`):
base-model `compute_logprobs` over a fixed prompt, and a fresh **rank-16**
`cross_entropy` `forward_backward` (LoRA `lora_B=0` at init ⇒ step-0 loss == base loss).

**Result — PASS, same band as RunPod** (hosted Tinker reference vs Modal HF):

| comparison | hosted Tinker | ours (Modal HF) | Δ |
|---|---|---|---|
| `compute_logprobs` (15 scored tokens) | — | — | median \|Δ\| **0.0037**, mean 0.024, max 0.16 nats |
| `forward_backward` `loss:sum` | 29.12152 | 28.91818 | **0.70%** (abs 0.203) |

The per-token logprob band (median 0.004, mean 0.024) matches M1/M2 and the RunPod 27B
run (median 0.026). The 0.70% `loss:sum` gap (vs RunPod's 0.171%) is bf16 inference-kernel
precision — dominated by the first token (logprob ≈ −9.4, where bf16 rounding is largest).

**How it was run — and the serving caveat that forced it.** Run via an **ephemeral
in-container entrypoint**, `modal run …::parity` (added to `app.py`), NOT over the
deployed HTTP endpoint:
```bash
OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B modal run open-tinker/deploy/modal/app.py::provision
OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B OPEN_TINKER_MODAL_GPU=H100 \
  modal run open-tinker/deploy/modal/app.py::parity        # prints PARITY_JSON
# hosted reference (needs TINKER_API_KEY):
OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B python deploy/parity_probe.py tinker both
```
Why not the deployed `/v1/logprobs`: the HF sampler **lazy-loads the base on first
request**, and a 27B load is ~2.5 min (851 tensors). Inside the asgi request that blows
the Modal **web-endpoint deadline** — the first request fails (observed:
`Heartbeat … Deadline exceeded`, client gets a malformed body). This is the same
"serving a large base over HTTP needs **load-at-startup**" limitation the `stress_test`
docstring documents for >100B. The in-container `parity` entrypoint sidesteps it (loads
in-process, no HTTP deadline) **and** avoids a lingering `min=1` control plane —
`modal run` is ephemeral and exits. Sampler and trainer each hold a full 27B (~54GB),
which together OOM one 80GB H100, so `parity` frees the sampler before building the trainer.

> Follow-up for *serving* (not parity): eager-load the base in `SamplerService.@enter`
> (or set a readiness gate) so the first HTTP request doesn't pay the cold load. Tracked
> as a productionization step; the engine correctness is what this run validates.

---

## Cost discipline (post-mortem)

The control plane is `min_containers=1` (always-warm H100, sticky training state) — it
does **not** scale to zero. **Always `modal app stop open-tinker` the moment a deploy-based
run (e.g. `fanout_demo.py`) is done.** A deploy left running idle for ~10h here exhausted
the workspace billing-cycle budget and stalled subsequent jobs ("waiting to be scheduled
on a CPU worker" → "spend limit reached"). The `parity` entrypoint avoids this entirely by
being ephemeral; prefer it / `modal run` over `modal deploy` whenever an HTTP endpoint
isn't strictly required.
