# open-tinker

A scoped, open reimplementation of the [Tinker](https://tinker.thinkingmachines.dev)
training/sampling SDK, backed by our own RunPod infra (see
`docs/specs/runpod-tinker-infra.md`).

**Goal:** be import- and behavior-compatible with the slice of the real `tinker`
SDK that `tinker_cookbook` and `battery/train/tinker` actually call, so those run
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

Milestone 1 — **SFT + sampling**. Scaffold stage: data types are implemented;
RPC methods raise `NotImplementedError` until the wire protocol (spec §5) and
backend land. See the repo task list.

## Layout

```
src/open_tinker/
  __init__.py          # public surface, mirrors the subset of tinker.__all__ we implement
  _config.py           # base_url / api_key resolution
  _futures.py          # APIFuture (awaitable + .result()), matching the SDK's submit-now/await-later model
  _exceptions.py       # TinkerError hierarchy (so cookbook retry handling compiles)
  _transport.py        # HTTP client to the control plane (STUB until §5)
  shim.py              # use_as_tinker()
  types/               # Datum, ModelInput, TensorData, AdamParams, SamplingParams, ... (implemented)
  clients/             # ServiceClient / TrainingClient / SamplingClient (signatures real, RPC bodies stubbed)
```
