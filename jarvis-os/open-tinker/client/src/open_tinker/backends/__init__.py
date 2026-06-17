"""Backend implementations of :class:`open_tinker.protocol.Backend`.

``HTTPBackend`` (here) talks to the control plane over the wire. The in-process
``LocalBackend`` lives in ``open_tinker_server`` (it needs the server engines),
and is injected into ``ServiceClient(backend=...)`` for single-process mode.
"""

from .http import HTTPBackend

__all__ = ["HTTPBackend"]
