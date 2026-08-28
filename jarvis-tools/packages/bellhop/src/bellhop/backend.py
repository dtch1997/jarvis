"""The backend seam: the provider-agnostic ephemeral-box contract.

Bellhop's identity is the imperative *check in -> run -> check out* lifecycle:
provision a disposable box, carry your code up (``push``), run steps against it
(``exec``), bring results back (``pull``), and check out (``teardown``). Two
providers implement that contract:

- **RunPod** — an SSH-able GPU/CPU pod (:class:`bellhop.pod.Pod`).
- **Modal** — an ephemeral Sandbox container (:class:`bellhop.modal_box.Sandbox`).

``run()`` / ``run_many()`` (see run.py) are written against this protocol and
pick a backend purely from the config type you hand them
(:class:`~bellhop.pod.PodConfig` -> RunPod, :class:`~bellhop.modal_box.ModalConfig`
-> Modal), via :func:`open_box`.

Every box context manager takes the same ``keep`` policy (:data:`KeepPolicy`):
``False`` always tears down, ``True`` never does, and ``"on-failure"`` keeps
the box only when the body raised — so a failed job can't take the only copy
of its outputs down with it.

:func:`bellhop.call.call` (remote function execution) is *derived* from these
primitives, not part of the protocol — it works over any ExecBox.
"""

from __future__ import annotations

import contextlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Literal, Protocol, runtime_checkable

from .errors import PreflightError

# Teardown policy for the box context managers (``pod()``, ``sandbox()``,
# ``open_box()``, ``run(keep_pod=...)``):
#   False        -> always tear down (the default)
#   True         -> never tear down
#   "on-failure" -> tear down only if the body finished cleanly; if it raised
#                   (job failed, upload failed, timeout, ...) leave the box up so
#                   whatever it holds — checkpoints, logs — can still be
#                   retrieved. The server-side TTL remains the cost backstop.
KeepPolicy = Literal[False, True, "on-failure"]


def should_teardown(keep: KeepPolicy, failed: bool, held: bool = False) -> bool:
    """Decide teardown from the keep policy, whether the body raised, and
    whether the box was explicitly held (:meth:`ExecBox.hold`)."""
    if keep is True or held:
        return False
    if keep == "on-failure":
        return not failed
    if keep is False:
        return True
    raise PreflightError(f"keep must be False, True or 'on-failure' (got {keep!r})")


def announce_kept_box(kind: str, box_id: str, teardown_hint: str,
                      why: str = "keep='on-failure'") -> None:
    """One loud stderr line when a box survives a failure — the id is the
    only handle the caller has for retrieving what's on it."""
    print(
        f"bellhop: {kind} {box_id} KEPT after failure ({why}). "
        f"Retrieve what you need, then tear it down: {teardown_hint}",
        file=sys.stderr, flush=True,
    )


# What push() leaves out of the codebase archive, on either backend.
TAR_EXCLUDES = ["--exclude=.git", "--exclude=__pycache__", "--exclude=.venv",
                "--exclude=node_modules", "--exclude=*.pyc"]


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


@runtime_checkable
class ExecBox(Protocol):
    """A live, execable ephemeral box. Both Pod and Sandbox satisfy this."""

    id: str

    # timeout: optional *client-side* cap in seconds; None (default) means no
    # client-side limit — the box's native server-side TTL (PodConfig
    # stop_after/terminate_after/max_lifetime, ModalConfig timeout/max_lifetime)
    # is the backstop. A finite timeout raises ExecTimeoutError when it expires.
    async def exec(self, cmd: str, env: dict[str, str] | None = None,
                   timeout: float | None = None) -> ExecResult: ...

    async def push(self, local: str | Path, remote: str) -> None: ...

    async def pull(self, remote: str, local_dest: str | Path) -> None: ...

    async def exists_remote(self, path: str) -> bool: ...

    async def teardown(self) -> None: ...

    # Ask the owning context manager NOT to tear this box down on exit,
    # whatever its ``keep`` policy — used when something irreplaceable is
    # still on the box (e.g. a salvage pull failed). Idempotent.
    def hold(self, reason: str) -> None: ...


@contextlib.asynccontextmanager
async def open_box(backend, *, keep: KeepPolicy = False,
                   api_key: str | None = None) -> AsyncIterator[ExecBox]:
    """Provision the box implied by ``backend``'s type, yield it, tear it down.

    ``keep`` is the teardown policy (see :func:`should_teardown`).

    Dispatches on the config class so callers never branch on provider:
    ``PodConfig`` -> RunPod pod, ``ModalConfig`` -> Modal sandbox. Imports are
    local so a RunPod-only install never needs ``modal`` (and vice versa).
    """
    # Local imports avoid a circular dependency (pod/modal_box import this
    # module for ExecResult) and keep provider deps optional.
    from .pod import PodConfig, pod

    if isinstance(backend, PodConfig):
        async with pod(backend, keep=keep, api_key=api_key) as p:
            yield p
        return

    from .modal_box import ModalConfig, sandbox

    if isinstance(backend, ModalConfig):
        async with sandbox(backend, keep=keep) as s:
            yield s
        return

    raise PreflightError(
        f"unknown backend config {type(backend).__name__!r}; "
        "expected PodConfig (RunPod) or ModalConfig (Modal)"
    )
