# Cookbook import-parity findings (task #2)

`tests/parity_cookbook.py` shims `open_tinker` in as `tinker`, then imports
`tinker_cookbook` and constructs every Config `battery/train/tinker` builds.
**7/7 checks pass.** Run it with the cookbook venv:

```
PYTHONPATH=open-tinker/src:battery/src \
  experiments/2026-06-15-em-distill-tinker-27b/.venv/bin/python \
  open-tinker/tests/parity_cookbook.py
```

## Surface gaps the cookbook forced (beyond what battery directly calls)

The cookbook touches more of the `tinker` surface *at import time* than battery
does at runtime. Found and closed:

1. **`tinker.types.ImageChunk` / `ImageAssetPointerChunk`** — referenced in
   `tinker_cookbook.renderers.base` module-level annotations (no
   `from __future__ import annotations` there, so they're evaluated on import).
   Added as minimal pydantic types; no backend behavior (images are a spec
   non-goal). Also made `ModelInputChunk` the real discriminated union.
2. **`tinker.types.tensor_data` submodule** — `recipes/rl_loop.py` does
   `from tinker.types.tensor_data import TensorData`. Aliased `types.tensors` as
   `types.tensor_data` and registered it in `sys.modules` via the shim.
3. **`tinker.lib.public_interfaces`** — the cookbook imports `APIFuture` from
   there and `RestClient` from `...rest_client`. Added the `lib/public_interfaces`
   package (re-exporting the canonical `APIFuture` + clients) and a stubbed
   `RestClient`; registered the dotted submodules in the shim. Added
   `ServiceClient.create_rest_client()`.

## Implication for the surface contract

`open_tinker.use_as_tinker()` must register these dotted submodules in
`sys.modules` (parent-package attributes aren't enough for dotted imports):
`tinker.types`, `tinker.types.tensor_data`, `tinker.lib`,
`tinker.lib.public_interfaces`, `tinker.lib.public_interfaces.rest_client`.

## Not gaps (test bugs fixed)

`recipe_name` is a required kwarg on both `supervised.train.Config` and
`train_on_policy.Config`; battery always passes it — my first hand-rolled config
omitted it. The CLI-driven checks (5–7) call battery's real `build_parser()` +
`build_config()`, so they can't drift from battery.
