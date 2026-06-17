"""Make ``import tinker`` resolve to ``open_tinker``.

``tinker_cookbook`` does ``import tinker`` / ``import tinker.types``. Calling
:func:`use_as_tinker` registers this package (and its ``types`` submodule) under
those names in ``sys.modules`` so the cookbook transparently uses our backend.

Call it BEFORE importing ``tinker_cookbook``. Idempotent. Raises if the real
``tinker`` is already imported, to avoid a half-shadowed state (in parity tests
you want both side-by-side: import the real ``tinker`` under its own name in a
separate process, not via this shim).
"""

from __future__ import annotations

import sys

__all__ = ["use_as_tinker"]


def use_as_tinker(force: bool = False) -> None:
    import open_tinker

    if "tinker" in sys.modules and not force:
        existing = sys.modules["tinker"]
        if existing is not open_tinker:
            raise RuntimeError(
                "The real `tinker` is already imported; refusing to shadow it. "
                "Call use_as_tinker() before importing tinker/tinker_cookbook, "
                "or pass force=True."
            )
        return
    sys.modules["tinker"] = open_tinker
    sys.modules["tinker.types"] = open_tinker.types
    # Register submodules the cookbook imports by dotted path (dotted imports
    # consult sys.modules, not just the parent package's attributes).
    import open_tinker.lib.public_interfaces as _pub
    import open_tinker.lib.public_interfaces.rest_client as _rest

    sys.modules["tinker.types.tensor_data"] = open_tinker.types.tensors
    sys.modules["tinker.lib"] = open_tinker.lib
    sys.modules["tinker.lib.public_interfaces"] = _pub
    sys.modules["tinker.lib.public_interfaces.rest_client"] = _rest
