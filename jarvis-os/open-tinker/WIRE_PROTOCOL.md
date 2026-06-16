# open-tinker wire protocol (v0, milestone 1)

JSON over HTTP between the `open_tinker` client and the control plane (spec §5).
**We own this protocol** — it only needs client+server agreement, not parity with
Tinker's private wire. Tensors go as base64 raw buffers (exact, compact) so the
numerical-parity gate (#8) isn't muddied by float-repr drift.

Auth: `Authorization: Bearer <api_key>` when a key is configured.

## Value encodings

**TensorData**
```json
{ "dtype": "float32|int64", "shape": [..],
  "data_b64": "<base64 of C-contiguous little-endian buffer>",
  "sparse_crow_indices": null, "sparse_col_indices": null }
```
Sparse CSR (used for `target_tokens`/`weights` when it saves space): `data_b64`
holds the non-zero values; `shape` is the dense shape; the two index arrays are
CSR row pointers / column indices.

**ModelInput** — `{ "tokens": [int, ..] }` (text-only; images are out of scope).

**Datum** — `{ "model_input": <ModelInput>, "loss_fn_inputs": { "<key>": <TensorData> } }`.
Loss keys by `loss_fn`:
- `cross_entropy`: `target_tokens` (int64), `weights` (float32)
- `importance_sampling`: `target_tokens`, `logprobs`, `mask`, `advantages` (float32)

## Endpoints

### `POST /v1/training/sessions` → create / resume a training client
Req: `{ base_model, lora: {rank, seed, train_mlp, train_attn, train_unembed} | null,
        from_state: "tinker://..." | null, user_metadata }`
Resp: `{ model_id, base_model }`
Server: allocate (or cold-start) a session on a training pod holding base model +
fresh LoRA (or restored full state) + optimizer in VRAM. Sticky: all subsequent
`{model_id}` RPCs route to the owning pod.

### `POST /v1/training/{model_id}/forward_backward` → accumulate grads
Req: `{ seq_id, loss_fn, loss_fn_config | null, data: [<Datum>, ..] }`
Resp: `{ loss_fn_output_type, loss_fn_outputs: [ {"<key>": <TensorData>} ], metrics: {..} }`
Server: forward+backward one microbatch, **accumulate** into `.grad` (do NOT step).
`metrics` carries at least `loss:sum` / `loss:mean` for the cookbook's logging.

### `POST /v1/training/{model_id}/optim_step` → Adam update
Req: `{ seq_id, adam_params: {learning_rate, beta1, beta2, eps, weight_decay, grad_clip_norm} }`
Resp: `{ metrics: {..} | null }`
Server: apply one Adam step over accumulated grads (honoring the exact params — see
parity gate), then zero grads.

### `POST /v1/training/{model_id}/save` → checkpoint
Req: `{ seq_id, kind: "state" | "sampler", name, ttl_seconds | null, overwrite }`
Resp: `{ path }`  (`tinker://<run>/weights/<id>` for state,
`tinker://<run>/sampler_weights/<id>` for sampler)
Server: persist full training state (optimizer included) or inference-only adapter
to the blob store; honor `ttl_seconds`.

### `POST /v1/training/{model_id}/load_state`
Req: `{ seq_id, path }` · Resp: `{ ok: true }`

### `POST /v1/sample` → generation (stateless; serverless worker)
Req: `{ model, weights_path | null, prompt: <ModelInput>, num_samples,
        sampling_params: {max_tokens, temperature, top_p, top_k, stop, seed},
        include_prompt_logprobs, topk_prompt_logprobs }`
Resp: `{ sequences: [ {tokens: [..], logprobs: [..]|null, stop_reason: "stop"|"length"} ],
         prompt_logprobs: [float|null, ..] | null }`
Note: `prompt_logprobs[0]` is `null` (no logprob for the first token) — preserved
through the client as `NaN`→`None`.

### `POST /v1/logprobs` → teacher-forced per-token logprobs (stateless)
Req: `{ model, weights_path | null, prompt: <ModelInput> }`
Resp: `{ logprobs: [float|null, ..] }`  (length = prompt length; index 0 is `null`)

### `GET /v1/capabilities`
Resp: `{ models: [..], loss_fns: [..], max_lora_rank: int, ... }`

## Ordering & idempotency
Per `model_id`, the client serializes submission FIFO (single-thread executor),
so `forward_backward`×N then `optim_step` arrive in order. `seq_id` is monotonic
per client; the server should reject/replay out-of-order or duplicate `seq_id`
to make retries safe. Sampling/logprobs are order-independent.

## Async model (v0)
v0 is request/response: the server blocks until the op completes and returns the
result; the client runs the POST on an executor and hands back an `APIFuture`, so
the cookbook's submit-now/await-later pipelining still works. A later revision may
switch to submit→`{request_id}`→poll/SSE if long ops need it.
