"""ModalFleet: sandboxes as Modal Sandboxes (gVisor).

Any machine with a Modal token can reach these sandboxes, so a trainer on a
RunPod pod (which can't run Docker) can still give every rollout its own
container. The contract is DockerFleet's, with these differences:

- **Images.** ``modal.Image.from_registry(ref)``. The first use of a ref
  builds it, which takes minutes for a multi-GB image. Later uses start in
  seconds. The image needs ``python`` and ``pip`` on PATH, or pass
  ``add_python=``. ``prefetch()`` builds images ahead of a run.
- **Limits.** CPU and memory go in as (request, limit) = (limit, limit), which
  matches Docker's hard caps. Modal has no pids knob and caps disk itself.
- **Lifetime.** ``max_lifetime`` is Modal's server-side timeout, so a sandbox
  the client forgot still dies on its own.
- **Network.** Blocked unless you pass an outbound allowlist, which Modal
  enforces outside the sandbox.
- **Kernel.** gVisor is a user-space kernel. Syscalls are slower and a few
  are unsupported, and running out of memory can kill the whole sandbox
  (SandboxError) where Docker kills one process.

``modal`` is an optional dependency (``pip install 'bellhop-py[modal]'``),
imported on first use.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
from collections.abc import Iterable, Sequence
from datetime import timedelta
from typing import Any

from ..errors import PreflightError, SandboxError
from ..modal_box import _import_modal
from .base import (
    CLIENT_GRACE_S,
    DEFAULT_SHELL,
    RUN_KEY,
    TIMEOUT_RC,
    BaseSandbox,
    CommandResult,
    Fleet,
    Limits,
    gather_timed,
    read_file_script,
    wrap_command,
    write_file_script,
)

NAME_KEY = "bellhop-fleet-name"   # Modal tag holding open()'s name_hint
MODAL_EXEC_TIMEOUT_RC = -1        # what ContainerProcess.wait() returns when exec(timeout=) fired


async def _drain(stream, cap: int | None, chunks: list[bytes]) -> bool:
    """Append ``stream`` to ``chunks``, keeping at most ``cap`` bytes in total.

    Keeps reading past the cap so the process can finish. Returns whether
    anything was dropped.
    """
    size = sum(len(c) for c in chunks)
    truncated = False

    def take(chunk) -> None:
        nonlocal size, truncated
        if isinstance(chunk, str):
            chunk = chunk.encode()
        if cap is None or size < cap:
            keep = chunk if cap is None else chunk[: cap - size]
            chunks.append(keep)
            size += len(keep)
            truncated |= len(keep) < len(chunk)
        else:
            truncated = True

    if hasattr(stream, "__aiter__"):
        async for chunk in stream:
            take(chunk)
    else:  # an SDK without streaming iteration: one read, capped afterwards
        take(await stream.read.aio())
    return truncated


class ModalSandbox(BaseSandbox):
    """One Modal Sandbox. Get it from :meth:`ModalFleet.open`."""

    def __init__(self, sb, image: str, shell: Sequence[str] = DEFAULT_SHELL):
        super().__init__(sb.object_id, image)
        self._sb = sb
        self.shell = tuple(shell)

    async def exec(self, command: str, *, workdir: str = "/", timeout: float = 60,
                   max_output_bytes: int | None = None) -> CommandResult:
        argv = wrap_command(command, workdir, timeout, self.shell)
        backstop = math.ceil(timeout) + CLIENT_GRACE_S      # Modal kills the exec here
        chunks: list[bytes] = []
        try:
            rc, truncated = await asyncio.wait_for(
                self._exec(argv, backstop, max_output_bytes, chunks), backstop + CLIENT_GRACE_S)
        except asyncio.TimeoutError:                         # the stream itself hung
            return CommandResult(TIMEOUT_RC, _text(chunks), timed_out=True)
        except Exception as e:  # noqa: BLE001 - any failure of the plumbing is infra
            if "timeout" in type(e).__name__.lower():        # modal's ExecTimeoutError
                return CommandResult(TIMEOUT_RC, _text(chunks), timed_out=True)
            raise SandboxError(f"{self.id}: modal exec failed: {type(e).__name__}: {e}") from e
        text = _text(chunks)
        if rc == MODAL_EXEC_TIMEOUT_RC:
            return CommandResult(TIMEOUT_RC, text, timed_out=True, truncated=truncated)
        # A command that killed the sandbox (OOM, kill 1) must not read as the workload's result.
        if rc != 0 and not await self._alive():
            raise SandboxError(f"{self.id}: sandbox terminated (rc={rc}): {text[-500:]}")
        return CommandResult(rc, text, timed_out=rc == TIMEOUT_RC, truncated=truncated)

    async def _exec(self, argv: list[str], backstop: int, cap: int | None,
                    chunks: list[bytes]) -> tuple[int, bool]:
        proc = await self._sb.exec.aio(*argv, timeout=backstop, text=False)
        truncated = await _drain(proc.stdout, cap, chunks)
        # The wrapper sends stderr to stdout; only a failure to start bash lands here.
        truncated |= await _drain(proc.stderr, cap, chunks)
        return await proc.wait.aio(), truncated

    async def write_file(self, path: str, content: str | bytes, executable: bool = False) -> None:
        data = content.encode() if isinstance(content, str) else content
        try:
            proc = await self._sb.exec.aio("/bin/sh", "-c", write_file_script(path, executable),
                                           timeout=120, text=False)
            proc.stdin.write(data)
            proc.stdin.write_eof()
            await proc.stdin.drain.aio()
            rc = await proc.wait.aio()
            err = b"" if rc == 0 else (await proc.stderr.read.aio() or b"")
        except Exception as e:  # noqa: BLE001
            raise SandboxError(f"{self.id}: write {path} failed: {type(e).__name__}: {e}") from e
        if rc != 0:
            raise SandboxError(f"{self.id}: write {path} failed (rc={rc}): "
                               f"{err.decode(errors='replace')[-500:]}")

    async def read_file(self, path: str, max_bytes: int | None = None) -> str:
        try:
            proc = await self._sb.exec.aio("/bin/sh", "-c", read_file_script(path, max_bytes),
                                           timeout=120, text=False)
            out = await proc.stdout.read.aio() or b""
            err = await proc.stderr.read.aio() or b""
            rc = await proc.wait.aio()
        except Exception as e:  # noqa: BLE001
            raise SandboxError(f"{self.id}: read {path} failed: {type(e).__name__}: {e}") from e
        if rc != 0:
            raise FileNotFoundError(f"{self.id}:{path}: {(err or out).decode(errors='replace')[-300:]}")
        return out.decode("utf-8", errors="replace")

    async def _alive(self) -> bool:
        try:
            return await self._sb.poll.aio() is None
        except Exception:  # noqa: BLE001 - can't ask means it's gone for our purposes
            return False

    async def _teardown(self) -> None:
        with contextlib.suppress(Exception):
            await self._sb.terminate.aio()


def _text(chunks: list[bytes]) -> str:
    return b"".join(chunks).decode("utf-8", errors="replace")


class ModalFleet(Fleet):
    """Sandboxes as Modal Sandboxes, anchored to one Modal app.

    ``block_network`` defaults to True unless an outbound allowlist is given.
    ``max_lifetime`` must be at most 24 h (Modal's ceiling).
    ``registry_secret`` is a ``modal.Secret`` holding REGISTRY_USERNAME and
    REGISTRY_PASSWORD for private registries.
    """

    backend = "modal"

    def __init__(self, run_id: str | None = None, *, limits: Limits | None = None,
                 max_live: int | None = None, app_name: str = "bellhop-fleet",
                 max_lifetime: timedelta = timedelta(hours=2), block_network: bool | None = None,
                 outbound_domain_allowlist: Sequence[str] | None = None,
                 outbound_cidr_allowlist: Sequence[str] | None = None,
                 region: str | None = None, add_python: str | None = None,
                 registry_secret: Any = None, shell: Sequence[str] = DEFAULT_SHELL):
        super().__init__(run_id, limits=limits, max_live=max_live, shell=shell)
        allowlist = bool(outbound_domain_allowlist or outbound_cidr_allowlist)
        if block_network is None:
            block_network = not allowlist
        if block_network and allowlist:
            raise PreflightError("block_network=True contradicts an outbound allowlist; pass one or the other")
        if not timedelta(seconds=1) <= max_lifetime <= timedelta(hours=24):
            raise PreflightError(f"Modal sandboxes live between 1 s and 24 h (got max_lifetime={max_lifetime})")
        self.app_name = app_name
        self.max_lifetime = max_lifetime
        self.block_network = block_network
        self.outbound_domain_allowlist = list(outbound_domain_allowlist or [])
        self.outbound_cidr_allowlist = list(outbound_cidr_allowlist or [])
        self.region = region
        self.add_python = add_python
        self.registry_secret = registry_secret
        self._images: dict[str, Any] = {}
        self._app = None
        self._app_lock: asyncio.Lock | None = None

    def create_kwargs(self, *, image: Any, app: Any, env: dict[str, str], limits: Limits,
                      name_hint: str = "sb") -> dict:
        """The ``modal.Sandbox.create`` kwargs for one sandbox (pure: no network)."""
        kw: dict = {
            "app": app,
            "image": image,
            "timeout": int(self.max_lifetime.total_seconds()),
            "cpu": (limits.cpu, limits.cpu),
            "memory": (limits.memory_mb, limits.memory_mb),
            "tags": {RUN_KEY: self.run_id, NAME_KEY: name_hint},
            "block_network": self.block_network,
        }
        if env:
            kw["env"] = dict(env)
        if self.outbound_domain_allowlist:
            kw["outbound_domain_allowlist"] = list(self.outbound_domain_allowlist)
        if self.outbound_cidr_allowlist:
            kw["outbound_cidr_allowlist"] = list(self.outbound_cidr_allowlist)
        if self.region:
            kw["region"] = self.region
        return kw

    def image(self, ref: str):
        """The (cached) ``modal.Image`` for a registry ref."""
        img = self._images.get(ref)
        if img is None:
            modal = _import_modal()
            kw: dict = {}
            if self.add_python:
                kw["add_python"] = self.add_python
            if self.registry_secret is not None:
                kw["secret"] = self.registry_secret
            img = self._images[ref] = modal.Image.from_registry(ref, **kw)
        return img

    async def app(self):
        if self._app is None:
            if self._app_lock is None:
                self._app_lock = asyncio.Lock()
            async with self._app_lock:
                if self._app is None:
                    modal = _import_modal()
                    self._app = await modal.App.lookup.aio(self.app_name, create_if_missing=True)
        return self._app

    async def _create(self, image: str, *, env: dict[str, str], limits: Limits,
                      name_hint: str) -> ModalSandbox:
        modal = _import_modal()
        try:
            app = await self.app()
            kw = self.create_kwargs(image=self.image(image), app=app, env=env, limits=limits,
                                    name_hint=name_hint)
            sb = await modal.Sandbox.create.aio(**kw)
        except PreflightError:
            raise
        except Exception as e:  # noqa: BLE001
            raise SandboxError(f"modal sandbox create failed for {image}: {type(e).__name__}: {e}") from e
        return ModalSandbox(sb, image, self.shell)

    async def gc(self) -> int:
        return await gc_modal(self.run_id, app_name=self.app_name)

    async def prefetch(self, images: Iterable[str], *, concurrency: int = 4) -> dict[str, float]:
        """Build the images on Modal. An image Modal already has takes ~0 s."""
        app = await self.app()

        async def one(ref: str) -> None:
            await self.image(ref).build.aio(app)

        return await gather_timed(images, one, concurrency)


async def gc_modal(run_id: str | None = None, *, app_name: str = "bellhop-fleet") -> int:
    """Terminate the app's running fleet sandboxes: one run's, or (``run_id=None``) all.

    Returns how many were terminated.
    """
    modal = _import_modal()
    app = await modal.App.lookup.aio(app_name, create_if_missing=True)
    n = 0
    async for sb in modal.Sandbox.list.aio(app_id=app.app_id, tags={RUN_KEY: run_id} if run_id else None):
        with contextlib.suppress(Exception):
            await sb.terminate.aio()
            n += 1
    return n
