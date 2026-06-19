# open-tinker

A scoped, open reimplementation of the [Tinker](https://tinker.thinkingmachines.dev)
training/sampling SDK, backed by our own RunPod infra (see
`docs/specs/runpod-tinker-infra.md`).

**Goal:** be import- and behavior-compatible with the slice of the real `tinker`
SDK that `tinker_cookbook` and `aligne/train/tinker` actually call, so those run
**unchanged** against our backend — escaping the hosted Tinker rate limit.

This is **strategy C** ("scoped SDK clone") from the spec. We deliberately do NOT
reproduce Tinker's entire public API — only the surface our consumers touch.

## Using it in place of `tinker`

The cookbook does `import tinker`. To make it resolve to this package:

```python
import open_tinker
open_tinker.use_as_tinker()      # registers open_tinker (+ submodules) as `tinker`
# ... now `import tinker` anywhere downstream gets open_tinker
```

Point it at our backend with `OPEN_TINKER_BASE_URL` (falls back to
`TINKER_BASE_URL`) and `OPEN_TINKER_API_KEY` / `TINKER_API_KEY`, or pass
`base_url=` / `api_key=` to `ServiceClient(...)`.

## Status

M1 (SFT + sampling), M2 (distillation), M3 (hybrid split) — the SDK surface the
cookbook + battery call is implemented and wire-tested. The client carries
`importance_sampling` inputs, `(T, K)` soft targets, and `topk_prompt_logprobs`
end to end. See `../README.md` for the per-milestone status and parity notes.

## Layout

```
src/open_tinker/
  __init__.py          # public surface, mirrors the subset of tinker.__all__ we implement
  _config.py           # base_url / api_key resolution
  _futures.py          # APIFuture (awaitable + .result()), matching the SDK's submit-now/await-later model
  _exceptions.py       # TinkerError hierarchy (so cookbook retry handling compiles)
  _transport.py        # HTTP client to the control plane (real httpx client + endpoint table + error mapping)
  _serialize.py        # wire (de)serialization for Datum / TensorData / soft targets
  protocol.py          # Backend / Trainer / Sampler protocols (the seam clients delegate to)
  backends/            # HTTPBackend — the concrete over-the-wire Backend
  shim.py              # use_as_tinker()
  types/               # Datum, ModelInput, TensorData, AdamParams, SamplingParams, ...
  clients/             # ServiceClient / TrainingClient / SamplingClient (delegate to a Backend)
  lib/                 # public_interfaces re-exports for tinker-compatible imports
```
