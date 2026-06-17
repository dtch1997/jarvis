# Spec: Self-hosted Tinker-compatible training infra on RunPod

**Status:** Implemented in [`open-tinker/`](../../open-tinker/) — M1 (SFT + sampling)
validated on a live H100; M2 (distillation) and M3 (hybrid split) code-complete.
See `open-tinker/README.md` for current per-milestone status and parity notes.
This document is kept as the original design rationale; where it and the code
disagree, the code wins.
**Author:** (you) + Claude
**Date:** 2026-06-16
**Goal:** Stand up our own RunPod-hosted training/sampling backend that the
existing `battery/train/tinker` drivers can use unchanged, to escape the hosted
Tinker rate limit.

---

## 1. Motivation

`battery/train/tinker` (the `battery-sft` / `battery-distill` /
`battery-distill-forward` CLIs) and the eval shim
(`battery/serving/tinker_shim.py`) all run against the **hosted Tinker service**.
That service rate-limits us, which throttles the EM-distill, character-training,
and model-organism work. We want a drop-in backend we control on RunPod, with no
rate limit, while keeping the clean Tinker programming model.

### Non-goals (v1)

- Reproducing Tinker's *entire* public SDK (sessions, audit logs, publish/
  unpublish, `forward_backward_custom`, RL `ppo` loss). We only build what our
  code calls — see §4.
- Multi-tenant SaaS, billing, quotas, a web console.
- Models we don't actually train. v1 targets the **Qwen3.6 family** (27B primary;
  235B is a stretch goal, see §9).
- RL / GRPO training loops. Only SFT + distillation (which the cookbook drives
  via the same primitives).

---

## 2. Decisions (locked with the user)

| Decision | Choice | Rationale |
|---|---|---|
| **Fidelity** | **C — scoped SDK clone** | Keep `tinker_cookbook`; reimplement only the `tinker` SDK methods/types the cookbook + battery actually call, pointed at our backend. `battery/train/tinker` runs **unchanged**. |
| **Compute** | **Hybrid** | Persistent GPU pod runs the stateful training daemon (model + optimizer live in VRAM across `forward_backward`/`optim_step`). Serverless workers handle stateless sampling / `compute_logprobs` given a checkpoint. |
| **First milestone** | **SFT + sampling** | `forward_backward(cross_entropy)` + `optim_step` + `save_state`/`load_state` + `SamplingClient.sample`. Unblocks `battery-sft` and eval. Distillation is milestone 2. |

The **scoped-clone** strategy means: we ship a Python package importable as
`tinker` (or a shim that the cookbook imports in its place) whose client classes
have the same signatures and observable semantics as the real SDK, but talk HTTP
to our RunPod backend. The cookbook never knows the difference; the delicate
`prompted_teacher.py` monkeypatch keeps working because it patches *cookbook*
internals, not the SDK.

---

## 3. What the code actually requires (the contract to hit)

Derived from reading `battery/src/battery/train/tinker/*` and
`battery/src/battery/serving/tinker_shim.py`, plus the installed `tinker`
package's `lib/public_interfaces/`.

### 3.1 Consumers

- **`sft.py`** → `tinker_cookbook.supervised.train.main(Config)` with
  `FromConversationFileBuilder`. Loss: **`cross_entropy`**.
- **`distill.py` reverse-KL** → `tinker_cookbook.distillation.train_on_policy`.
  Needs **on-policy rollouts** (sampler), **teacher logprobs**
  (`compute_logprobs_async`), loss **`importance_sampling`**, KL penalty.
- **`distill.py` forward-KL** → `train_off_policy` with `n_teacher_targets`
  (top-k soft targets from teacher) — milestone 2.
- **`prompted_teacher.py`** → raw `tinker.ModelInput.from_ints`,
  `tinker.TensorData.from_torch`, `SamplingClient.compute_logprobs_async`;
  monkeypatches `train_on_policy.incorporate_kl_penalty`.
- **`tinker_shim.py`** (eval) → `SamplingClient.sample` and
  `SamplingClient.compute_logprobs` (teacher-forced per-token logprobs), selecting
  arm by base-model name or `tinker://.../sampler_weights/...` path.

### 3.2 Core SDK surface to implement (and ONLY this)

**`ServiceClient`**
- `create_lora_training_client(base_model, rank) -> TrainingClient`
- `create_training_client_from_state(path) -> TrainingClient` (resume)
- `create_sampling_client(base_model | model_path) -> SamplingClient`
- `get_server_capabilities()` (cookbook probes this)

**`TrainingClient`** (stateful)
- `forward_backward(data: list[Datum], loss_fn, loss_fn_config) -> APIFuture[ForwardBackwardOutput]`
- `optim_step(AdamParams) -> APIFuture[OptimStepResponse]`
- `save_state(name, ttl_seconds, overwrite) -> APIFuture[SaveWeightsResponse]` (full state incl. optimizer → `tinker://` path)
- `load_state(path)`
- `save_weights_for_sampler(name) -> APIFuture` (inference-only weights → `tinker://.../sampler_weights/...`)
- `save_weights_and_get_sampling_client(name) -> SamplingClient`
- `get_tokenizer() -> PreTrainedTokenizer`
- `get_info()`

**`SamplingClient`** (stateless given weights)
- `sample(prompt: ModelInput, num_samples, sampling_params, include_prompt_logprobs, topk_prompt_logprobs) -> Future[SampleResponse]` + `sample_async`
- `compute_logprobs(prompt) / compute_logprobs_async(prompt) -> list[float|None]`
- `get_tokenizer`, `get_base_model`

**Types** (`tinker.types`, pydantic-compatible): `Datum`, `ModelInput`
(+ `.from_ints`/`.to_ints`/`ModelInputChunk`/`EncodedTextChunk`), `TensorData`
(+ `.from_torch`/`.to_torch`/`TensorDtype`), `AdamParams`, `SamplingParams`,
`LoraConfig`, `SampledSequence`, `SampleResponse`, `ForwardBackwardOutput`,
`OptimStepResponse`, `SaveWeightsResponse`, `Checkpoint`/`CheckpointType`,
`StopReason`, `ModelID`. Plus the exception hierarchy (`TinkerError`,
`APIStatusError`, `RateLimitError`, …) so cookbook's retry handling compiles.

**The `APIFuture` model.** Real SDK methods return immediately with an
`APIFuture` (backed by a thread `concurrent.futures.Future`) that is `await`-able
and has `.result()`. We replicate this: submit returns a future that resolves
when the backend RPC completes. This lets the cookbook pipeline
`forward_backward` calls without blocking.

### 3.3 Semantics we MUST match (the real risk — see §8 validation)

1. **Accumulation:** N×`forward_backward` calls accumulate gradients; one
   `optim_step` applies Adam and zeroes them. (Cookbook splits a batch into
   microbatches this way.)
2. **`loss_fn` contract & `loss_fn_inputs` shapes:**
   - `cross_entropy`: `Datum.loss_fn_inputs = {target_tokens, weights}`; loss is
     token-mean NLL over weighted positions.
   - `importance_sampling`: `loss_fn_inputs = {target_tokens, logprobs, mask,
     advantages}`; the policy-gradient surrogate the on-policy distill loop
     fills in (see `prompted_teacher.py`, which reads/writes exactly these keys).
3. **`compute_logprobs(prompt)`** returns per-position teacher-forced logprobs
   aligned to input tokens, with `None` at the first position — the `[S+1:]`
   re-alignment in `prompted_teacher.py` depends on this exact convention.
4. **`tinker://` paths:** opaque handles resolvable by `load_state` /
   `create_sampling_client` / the eval shim. Two kinds: full training state and
   `sampler_weights` (inference-only).
5. **Tokenizer/renderer parity:** `get_tokenizer(model)` must match what the
   cookbook's `qwen3_5_disable_thinking` renderer expects. We reuse the HF
   tokenizer, so this is free if `base_model` names match.

---

## 4. Architecture

```
  ┌─────────────────────────── client side (unchanged battery code) ──────────────────────────┐
  │  battery-sft / battery-distill  →  tinker_cookbook  →  import tinker (OUR scoped clone)     │
  │  battery-tinker-shim (eval)      →  tinker.SamplingClient                                   │
  └───────────────────────────────────────────────┬───────────────────────────────────────────┘
                                                   │ HTTPS (our wire protocol, §5)
                  ┌────────────────────────────────┼──────────────────────────────────┐
                  │                                 │                                  │
        ┌─────────▼──────────┐          ┌───────────▼───────────┐          ┌───────────▼─────────┐
        │  Control plane     │          │  Training pod (persist)│          │ Sampling workers    │
        │  (small always-on) │          │  RunPod GPU pod        │          │ RunPod serverless   │
        │  - session/run reg │          │  - 1 daemon per run    │          │  - vLLM + LoRA      │
        │  - tinker:// → blob │◄────────►│  - model+optim in VRAM │          │  - autoscale 0..N   │
        │  - job queue/router │          │  - fwd_bwd / optim_step│          │  - load sampler wts │
        └─────────┬──────────┘          │  - save→ blob store    │          └───────────┬─────────┘
                  │                      └───────────┬───────────┘                      │
                  └──────────────────────► RunPod Network Volume / S3 (checkpoint blob store) ◄────┘
```

### 4.1 Components

**A. Scoped SDK clone (`our_tinker`)** — pip-installable package that *is*
`tinker` from the cookbook's POV (installed in place of, or shadowing, the real
package). Pure client: serializes `Datum`/`ModelInput`/`TensorData`, calls the
control plane, wraps responses in `APIFuture`. No GPU deps.

**B. Control plane** — small always-on service (a cheap RunPod CPU pod or
Cloudflare/Fly box). Responsibilities:
- Auth (shared token; we're single-tenant).
- `create_lora_training_client` → allocate/attach a **training session** on a
  training pod (spin up if needed), return a `model_id`.
- Route `forward_backward`/`optim_step`/`save_state` RPCs to the owning pod
  (sticky by `model_id`).
- Resolve `tinker://` paths ↔ blob-store keys.
- Dispatch `sample`/`compute_logprobs` to serverless workers, passing the
  resolved weights handle.

**C. Training pod (persistent, stateful)** — one long-lived GPU pod (A100/H100
80GB for 27B LoRA). Runs a daemon that, per active session:
- Holds base model + LoRA adapter + Adam state in VRAM.
- Implements `forward_backward` (accumulate grads), `optim_step` (Adam update),
  `save_state`/`save_weights_for_sampler` (push to blob store, return
  `tinker://`), `load_state`.
- Backed by PyTorch + PEFT (LoRA) + the HF model. (vLLM is inference-only, so
  the training side is plain HF/PEFT or a thin trainer.)

**D. Sampling workers (serverless, stateless)** — RunPod serverless endpoint
running **vLLM** with LoRA-adapter hot-loading. Given a `sampler_weights`
`tinker://` handle: pull adapter from blob store, serve `sample` /
`compute_logprobs` (vLLM `prompt_logprobs`). Scales to zero when idle — this is
where the hybrid model saves money. (The existing `tinker_shim.py` already speaks
this shape; v1 can even reuse its rendering logic server-side.)

**E. Blob store** — RunPod **Network Volume** (simplest; mounts on pods) or
S3-compatible. Stores full training state and sampler weights, keyed by the
`tinker://` path. TTL support for `save_state(ttl_seconds=...)`.

### 4.2 Why hybrid (recap)

Training is inherently stateful (optimizer + adapter must persist in VRAM across
many `forward_backward`→`optim_step` cycles), so a **persistent pod** is the
natural fit and avoids re-loading multi-GB state per call. Sampling is stateless
given a checkpoint, bursty (rollouts, evals), and parallelizable — **serverless**
autoscaling fits and idles to zero. Putting both on persistent pods would burn
money on idle samplers; putting training on serverless would mean reloading
optimizer state every microbatch. Hence the split.

---

## 5. Wire protocol

Internal HTTP/JSON (or gRPC) between our SDK clone and control plane — **we own
it**, it does not need to match Tinker's private protocol, only our client and
server must agree. Sketch (REST):

| Method call | Endpoint | Notes |
|---|---|---|
| `create_lora_training_client` | `POST /v1/training/sessions` | body: base_model, lora rank/config → `{model_id}` |
| `forward_backward` | `POST /v1/training/{model_id}/forward_backward` | body: serialized `data`, `loss_fn`, config → `{request_id}`; poll/stream for `ForwardBackwardOutput` |
| `optim_step` | `POST /v1/training/{model_id}/optim_step` | body: AdamParams |
| `save_state` / `save_weights_for_sampler` | `POST /v1/training/{model_id}/save` | type=state\|sampler → `{tinker_path}` |
| `load_state` | `POST /v1/training/sessions` | from_state=path |
| `sample` | `POST /v1/sample` | body: weights handle, ModelInput, SamplingParams → routed to serverless |
| `compute_logprobs` | `POST /v1/logprobs` | body: weights handle, ModelInput |
| `get_server_capabilities` | `GET /v1/capabilities` | static-ish |

**Serialization:** `ModelInput`/`TensorData`/`Datum` already have
`to_ints`/`from_ints`/`to_torch`/`from_torch`; we encode tensors as
dtype+shape+base64 bytes (or msgpack) to keep `forward_backward` payloads compact.
**Async:** submit returns `request_id`; client `APIFuture` long-polls or holds an
SSE/websocket. Match the real SDK's "submit now, await later" so cookbook
pipelining is preserved.

---

## 6. Milestones

### M1 — SFT + sampling (the committed first slice)
1. **SDK clone skeleton**: `ServiceClient`, `TrainingClient`, `SamplingClient`,
   types, `APIFuture`, exceptions. Import-compatible; unit-test that
   `tinker_cookbook.supervised.train` imports and builds a `Config` against it.
2. **Training daemon**: HF + PEFT LoRA on one persistent pod.
   `forward_backward(cross_entropy)` with grad accumulation, `optim_step(Adam)`,
   `save_state`/`load_state`, `save_weights_for_sampler` → Network Volume.
3. **Control plane**: session create/route, `tinker://` resolver.
4. **Sampling worker**: vLLM serverless, LoRA hot-load, `sample` +
   `compute_logprobs`.
5. **End-to-end**: `battery-sft --smoke` trains a tiny LoRA and saves a
   checkpoint; `battery-tinker-shim` serves eval from it.
6. **Parity validation** (§8) on the SFT path.

**M1 exit criteria:** `battery-sft` (real, not smoke) on Qwen3.6-27B produces a
checkpoint whose train-loss curve and a held-out eval match a hosted-Tinker run
of the same config within tolerance.

### M2 — Distillation
- `importance_sampling` loss + advantages/mask plumbing; on-policy rollout loop
  (sampler in the train loop); verify `prompted_teacher.py` monkeypatch and the
  `[S+1:]` re-alignment work end-to-end. Then `train_off_policy` (`n_teacher_targets`
  top-k soft targets).

### M3 — Hardening
- Multi-run scheduling on the training pod (or pod-per-run autoscale), checkpoint
  GC/TTL, retries/idempotency, wandb passthrough, cost dashboard.

---

## 7. Open questions / risks

- **Server-side loss & optimizer parity** (highest risk). We can only partially
  observe how hosted Tinker computes `importance_sampling` and accumulates grads.
  Mitigation: §8 numerical validation before trusting any run.
- **Training backend choice**: plain HF+PEFT vs. a faster trainer (e.g.
  torchtune / a custom FSDP loop). 27B LoRA fits one 80GB GPU; 235B needs
  multi-GPU/multi-node (stretch).
- **vLLM LoRA hot-swap latency**: cold-loading an adapter per serverless request
  may dominate short rollouts. May need a warm pool or adapter cache.
- **Concurrency on the training pod**: one session per GPU initially. Multiple
  concurrent runs → pod-per-run (autoscale) or time-sharing.
- **`get_server_capabilities` shape**: must return enough for cookbook's feature
  probes; reverse from the installed package.
- **Tokenizer/renderer drift**: keep `base_model` names identical to hosted
  Tinker so the cookbook's renderer assumptions hold.

---

## 8. Validation plan (de-risking strategy C)

The whole bet of approach C is "our backend behaves like Tinker's." We prove it,
not assume it:

1. **Unit/import parity**: cookbook imports our `tinker`, builds every `Config`
   our drivers use, no attribute errors.
2. **Single-step numerical diff**: same `base_model`, same fixed `Datum` batch,
   same seed → compare `ForwardBackwardOutput.loss` and post-`optim_step` adapter
   weights between hosted Tinker and ours. Expect bitwise-close cross-entropy
   loss; small tolerance on weights (kernel/Adam-eps differences).
3. **Logprob parity**: `compute_logprobs` on a fixed prompt vs. hosted Tinker and
   vs. a local HF teacher-forced reference; assert the `None`-at-0 convention and
   `[S+1:]` alignment hold.
4. **End-to-end SFT curve**: run `battery-sft` on a small real dataset on both
   backends; train-loss curves and a held-out metric should track.
5. Only after 1–4 pass do we route real EM-distill / character-training jobs.

---

## 9. Cost & capacity (rough, to size the spend)

- **Training pod**: 1× H100 80GB persistent for 27B LoRA. Idle cost is the price
  of statefulness — mitigate by stopping the pod between campaigns (control plane
  can cold-start on first `create_lora_training_client`).
- **Sampling**: serverless, scale-to-zero; pay per rollout/eval burst.
- **235B stretch**: multi-GPU (e.g. 8×H100) training node + tensor-parallel vLLM
  samplers — defer past M2; sanity-check the architecture holds before committing.

---

## 10. Appendix — exact call sites in `battery`

- `battery/src/battery/train/tinker/sft.py` — `tinker_cookbook.supervised.train`
  (`cross_entropy`).
- `battery/src/battery/train/tinker/distill.py` — `train_on_policy`
  (`importance_sampling`) + `train_off_policy` (`n_teacher_targets`).
- `battery/src/battery/train/tinker/prompted_teacher.py` — raw `tinker.ModelInput`,
  `tinker.TensorData`, `compute_logprobs_async`; patches
  `train_on_policy.incorporate_kl_penalty`.
- `battery/src/battery/train/tinker/data.py` — `PromptOnlyDatasetBuilder`,
  `renderers.get_renderer`, `get_tokenizer` (all cookbook-side; needs our
  tokenizer parity only).
- `battery/src/battery/serving/tinker_shim.py` — `SamplingClient.sample` +
  `compute_logprobs`; arm selection by base model or `tinker://.../sampler_weights/...`.
