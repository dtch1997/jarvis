"""The fleet contract: what every sandbox backend provides.

The command semantics are ported from ``agentrl.sandbox``
(ArcadiaImpact/science-of-rl-motivations, PR #24). That module ported them
from Xiaomi's mimoagent backends (kubernetes.py, modal.py):

    timeout T /bin/bash -lc "exec 2>&1 </dev/null; cd <workdir> && <command>"

stderr is merged into stdout the way a terminal interleaves them, and stdin
is closed so nothing blocks on it. Exit code 124 means the in-sandbox timeout
fired. Design notes: docs/design/sandbox-fleet.md.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import re
import shlex
import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..errors import PreflightError, SandboxError

TIMEOUT_RC = 124              # what `timeout` exits with when the command ran out of time
CLIENT_GRACE_S = 30           # the client gives up this long after the in-sandbox timeout
RUN_KEY = "bellhop-fleet-run" # Docker label / Modal tag that carries the run id
DEFAULT_SHELL = ("/bin/bash", "-lc")


@dataclass(frozen=True)
class Limits:
    """Per-sandbox resources: ``cpu`` in cores, ``memory_mb`` in MiB.

    ``pids`` and ``disk_gb`` apply on Docker only. Modal has no pids knob and
    caps disk itself. ``disk_gb=None`` means no disk guard.
    """

    cpu: float = 2.0
    memory_mb: int = 4096
    pids: int | None = 4096
    disk_gb: float | None = None

    def __post_init__(self):
        if self.cpu <= 0 or self.memory_mb <= 0:
            raise PreflightError(f"Limits need cpu > 0 and memory_mb > 0 (got {self})")


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: str                 # stdout and stderr, interleaved
    timed_out: bool = False
    truncated: bool = False     # output passed max_output_bytes and was cut


@runtime_checkable
class Sandbox(Protocol):
    """One isolated container, driven command by command."""

    id: str
    image: str
    started_at: float           # wall clock (time.time()) when the sandbox came up
    ended_at: float | None

    async def exec(self, command: str, *, workdir: str = "/", timeout: float = 60,
                   max_output_bytes: int | None = None) -> CommandResult: ...

    async def write_file(self, path: str, content: str | bytes, executable: bool = False) -> None: ...

    async def read_file(self, path: str, max_bytes: int | None = None) -> str: ...

    async def close(self) -> None: ...


def wrap_command(command: str, workdir: str, timeout: float,
                 shell: Sequence[str] = DEFAULT_SHELL) -> list[str]:
    """The argv that runs ``command`` in ``workdir`` under an in-sandbox timeout."""
    body = f"exec 2>&1 </dev/null\ncd {shlex.quote(workdir)} && {command}"
    # `timeout 0` would disable the timeout, so round up and floor at 1 s.
    return ["timeout", str(max(1, math.ceil(timeout))), *shell, body]


def write_file_script(path: str, executable: bool) -> str:
    """The shell script that stores stdin at ``path``, creating parent dirs."""
    q = shlex.quote(path)
    return f'mkdir -p "$(dirname {q})" && cat > {q}' + (f" && chmod +x {q}" if executable else "")


def read_file_script(path: str, max_bytes: int | None) -> str:
    q = shlex.quote(path)
    return f"head -c {int(max_bytes)} {q}" if max_bytes else f"cat {q}"


_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_name(text: str, limit: int = 40) -> str:
    """Squash text into a Docker/Modal-safe name fragment."""
    return (_UNSAFE.sub("-", text).strip("-.") or "x")[:limit]


class _Slots:
    """Caps live sandboxes. ``acquire(n)`` takes n slots at once, so two
    half-served groups can never deadlock each other."""

    def __init__(self, capacity: int | None):
        if capacity is not None and capacity < 1:
            raise PreflightError(f"max_live must be >= 1 or None (got {capacity})")
        self.capacity = capacity
        self.used = 0
        self._cond: asyncio.Condition | None = None

    def _condition(self) -> asyncio.Condition:
        # Built on first use so a fleet can be constructed outside a running loop.
        if self._cond is None:
            self._cond = asyncio.Condition()
        return self._cond

    async def acquire(self, n: int = 1) -> None:
        if self.capacity is not None and n > self.capacity:
            raise PreflightError(f"{n} sandboxes can never fit max_live={self.capacity}")
        cond = self._condition()
        async with cond:
            await cond.wait_for(lambda: self.capacity is None or self.used + n <= self.capacity)
            self.used += n

    async def release(self, n: int = 1) -> None:
        cond = self._condition()
        async with cond:
            self.used -= n
            cond.notify_all()


class BaseSandbox:
    """Shared bookkeeping: timestamps, idempotent close, slot release."""

    def __init__(self, id: str, image: str):
        self.id = id
        self.image = image
        self.started_at = time.time()
        self.ended_at: float | None = None
        self._fleet: Fleet | None = None
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.ended_at = time.time()
        try:
            await self._teardown()
        finally:
            if self._fleet is not None:
                await self._fleet._released(self)

    async def _teardown(self) -> None:  # pragma: no cover - backends override
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, image={self.image!r})"


class Fleet:
    """Hands out sandboxes for one run and cleans up after it.

    Use it as an async context manager: on exit it closes every sandbox it
    still holds and sweeps its run id (``gc()``), which catches sandboxes a
    crashed caller never closed. Backends implement ``_create``, ``gc`` and
    ``prefetch``.
    """

    backend = "base"

    def __init__(self, run_id: str | None = None, *, limits: Limits | None = None,
                 max_live: int | None = None, shell: Sequence[str] = DEFAULT_SHELL):
        # The label/tag carries the run id verbatim; names use safe_name(run_id).
        self.run_id = run_id or f"fleet-{uuid.uuid4().hex[:8]}"
        self.limits = limits or Limits()
        self.shell = tuple(shell)
        self._slots = _Slots(max_live)
        self._live: dict[str, BaseSandbox] = {}

    @property
    def max_live(self) -> int | None:
        return self._slots.capacity

    @property
    def live(self) -> list[BaseSandbox]:
        """The sandboxes this fleet opened and hasn't closed yet."""
        return list(self._live.values())

    async def open(self, image: str, *, env: Mapping[str, str] | None = None,
                   limits: Limits | None = None, name_hint: str = "sb") -> BaseSandbox:
        """Start a sandbox from ``image``; waits for a slot when ``max_live`` is full.

        Raises :class:`~bellhop.errors.SandboxError` when the backend can't
        start it.
        """
        await self._before_open()
        await self._slots.acquire(1)
        try:
            sb = await self._create(image, env=dict(env or {}), limits=limits or self.limits,
                                    name_hint=safe_name(name_hint, 24))
        except BaseException:
            await self._slots.release(1)
            raise
        sb._fleet = self
        self._live[sb.id] = sb
        return sb

    async def _released(self, sb: BaseSandbox) -> None:
        if self._live.pop(sb.id, None) is not None:
            await self._slots.release(1)

    async def _before_open(self) -> None:
        """Backend hook run before each open (Docker waits on its disk floor)."""

    async def _create(self, image: str, *, env: dict[str, str], limits: Limits,
                      name_hint: str) -> BaseSandbox:  # pragma: no cover - backends override
        raise NotImplementedError

    async def gc(self) -> int:  # pragma: no cover - backends override
        """Remove every sandbox tagged with this fleet's run id; returns the count."""
        raise NotImplementedError

    async def prefetch(self, images: Iterable[str], *,
                       concurrency: int = 4) -> dict[str, float]:  # pragma: no cover
        """Make ``images`` ready to start; returns seconds spent per image."""
        raise NotImplementedError

    async def aclose(self) -> None:
        """Close every live sandbox, then sweep the run id."""
        await asyncio.gather(*(sb.close() for sb in self.live), return_exceptions=True)
        with contextlib.suppress(Exception):
            await self.gc()

    async def __aenter__(self) -> Fleet:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()


async def gather_timed(items: Iterable[str], one, concurrency: int) -> dict[str, float]:
    """Run ``one(item)`` over distinct items with a concurrency cap and time each.

    Collects every failure before raising one SandboxError that names them all.
    """
    sem = asyncio.Semaphore(max(1, concurrency))
    timings: dict[str, float] = {}
    errors: dict[str, str] = {}

    async def run(item: str) -> None:
        async with sem:
            t0 = time.monotonic()
            try:
                await one(item)
            except Exception as e:  # noqa: BLE001 - reported together below
                errors[item] = f"{type(e).__name__}: {e}"[:300]
                return
            timings[item] = round(time.monotonic() - t0, 2)

    await asyncio.gather(*(run(i) for i in dict.fromkeys(items)))
    if errors:
        lines = "\n".join(f"  {k}: {v}" for k, v in errors.items())
        raise SandboxError(f"prefetch failed for {len(errors)} image(s):\n{lines}")
    return timings
