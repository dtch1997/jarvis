"""DockerFleet: sandboxes as containers on the local Docker daemon.

A port of ``agentrl.sandbox`` (ArcadiaImpact/science-of-rl-motivations, PR
#24), which ran the realistic-rl-pipeline phases B–D. It keeps the same
``docker`` argv, the same container-gone check and the same two disk
protections:

- **Disk guard.** Docker on ext4 can't cap a container's writable layer. One
  rollout once filled the host disk (~60 GB) before its group was torn down.
  The guard kills any sandbox whose writable layer passes ``Limits.disk_gb``.
  Its next exec then raises SandboxError, so the rollout is masked as an
  infra failure. ``fleet.disk_killed`` names the victims.
- **Host floor.** ``open()`` waits while Docker's data disk has less than
  ``min_free_gb`` free, and gives up with SandboxError after ``free_wait_s``.

Only the ``docker`` CLI is needed, not the Python SDK.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone

from ..errors import PreflightError, SandboxError
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
    safe_name,
    wrap_command,
    write_file_script,
)

logger = logging.getLogger(__name__)


async def _run(argv: Sequence[str], *, stdin: bytes | None = None, timeout: float,
               max_output_bytes: int | None = None) -> tuple[int, bytes, bool, bool]:
    """Run argv locally: (returncode, output, client_timed_out, truncated).

    stderr is merged into stdout. Output past ``max_output_bytes`` is dropped
    while the process keeps draining, so it can still exit.
    """
    proc = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    chunks: list[bytes] = []
    size = 0
    truncated = False

    async def pump() -> None:
        nonlocal size, truncated
        if stdin is not None:
            proc.stdin.write(stdin)
            await proc.stdin.drain()
            proc.stdin.close()
        while True:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            if max_output_bytes is None or size < max_output_bytes:
                keep = chunk if max_output_bytes is None else chunk[: max_output_bytes - size]
                chunks.append(keep)
                size += len(keep)
                truncated |= len(keep) < len(chunk)
            else:
                truncated = True
        await proc.wait()

    try:
        await asyncio.wait_for(pump(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, b"".join(chunks), True, truncated
    return proc.returncode, b"".join(chunks), False, truncated


def _container_gone(text: str) -> bool:
    return "No such container" in text or "is not running" in text


class DockerSandbox(BaseSandbox):
    """One container. Get it from :meth:`DockerFleet.open`."""

    def __init__(self, id: str, image: str, network: str, shell: Sequence[str] = DEFAULT_SHELL):
        super().__init__(id, image)
        self.network = network
        self.shell = tuple(shell)
        self.ip: str | None = None   # on ``network``; lets a proxy log be joined to this sandbox

    async def exec(self, command: str, *, workdir: str = "/", timeout: float = 60,
                   max_output_bytes: int | None = None) -> CommandResult:
        argv = ["docker", "exec", self.id, *wrap_command(command, workdir, timeout, self.shell)]
        rc, out, client_to, truncated = await _run(argv, timeout=timeout + CLIENT_GRACE_S,
                                                   max_output_bytes=max_output_bytes)
        text = out.decode("utf-8", errors="replace")
        # The workload can print docker's error text too, so confirm with inspect.
        if rc != 0 and _container_gone(text) and not await self._alive():
            raise SandboxError(f"{self.id}: container unavailable: {text[-500:]}")
        return CommandResult(exit_code=TIMEOUT_RC if client_to else rc, output=text,
                             timed_out=client_to or rc == TIMEOUT_RC, truncated=truncated)

    async def write_file(self, path: str, content: str | bytes, executable: bool = False) -> None:
        data = content.encode() if isinstance(content, str) else content
        rc, out, _, _ = await _run(["docker", "exec", "-i", self.id, "/bin/sh", "-c",
                                    write_file_script(path, executable)], stdin=data, timeout=120)
        if rc != 0:
            raise SandboxError(f"{self.id}: write {path} failed (rc={rc}): "
                               f"{out.decode(errors='replace')[-500:]}")

    async def read_file(self, path: str, max_bytes: int | None = None) -> str:
        rc, out, _, _ = await _run(["docker", "exec", self.id, "/bin/sh", "-c",
                                    read_file_script(path, max_bytes)], timeout=120)
        if rc != 0:
            raise FileNotFoundError(f"{self.id}:{path}: {out.decode(errors='replace')[-300:]}")
        return out.decode("utf-8", errors="replace")

    async def _alive(self) -> bool:
        rc, out, _, _ = await _run(["docker", "inspect", "-f", "{{.State.Running}}", self.id], timeout=60)
        return rc == 0 and out.decode().strip() == "true"

    async def _teardown(self) -> None:
        await _run(["docker", "rm", "-f", self.id], timeout=120)


class DockerFleet(Fleet):
    """Sandboxes as containers on the local Docker daemon.

    ``network`` is any Docker network name: ``"none"`` (the default: no
    egress), ``"bridge"``, or a network you created (for example an internal
    one whose only way out is a logging proxy). ``env`` passed to ``open()``
    shows up in ``docker inspect``, so keep secrets out of it.
    """

    backend = "docker"

    def __init__(self, run_id: str | None = None, *, limits: Limits | None = None,
                 max_live: int | None = None, network: str = "none",
                 min_free_gb: float | None = 20.0, free_wait_s: float = 600.0,
                 guard_interval_s: float = 10.0, create_timeout_s: float = 600.0,
                 shell: Sequence[str] = DEFAULT_SHELL):
        super().__init__(run_id, limits=limits, max_live=max_live, shell=shell)
        self.network = network
        self.min_free_gb = min_free_gb
        self.free_wait_s = free_wait_s
        self.guard_interval_s = guard_interval_s
        self.create_timeout_s = create_timeout_s
        self.disk_killed: set[str] = set()
        self._caps: dict[str, float] = {}          # container name -> writable-layer cap, bytes
        self._guard: asyncio.Task | None = None
        self._data_dirs: list[str] | None = None

    # --- opening -------------------------------------------------------------------------

    async def _before_open(self) -> None:
        if shutil.which("docker") is None:
            raise PreflightError("DockerFleet needs the docker CLI on PATH")
        if not self.min_free_gb:
            return
        floor = self.min_free_gb * 1e9
        deadline = time.monotonic() + self.free_wait_s
        while (free := await self.free_bytes()) < floor:
            if time.monotonic() > deadline:
                raise SandboxError(
                    f"Docker's disk has {free / 1e9:.1f} GB free, under the {self.min_free_gb:.0f} GB "
                    f"floor, for {self.free_wait_s:.0f}s; not starting sandboxes")
            await asyncio.sleep(10)

    async def _create(self, image: str, *, env: dict[str, str], limits: Limits,
                      name_hint: str) -> DockerSandbox:
        name = f"bellhop-{safe_name(self.run_id, 32)}-{name_hint}-{uuid.uuid4().hex[:8]}"
        argv = ["docker", "run", "-d", "--name", name, "--label", f"{RUN_KEY}={self.run_id}",
                "--network", self.network, "--cpus", f"{limits.cpu:g}",
                "--memory", f"{limits.memory_mb}m", "--memory-swap", f"{limits.memory_mb}m", "--init"]
        if limits.pids:
            argv += ["--pids-limit", str(limits.pids)]
        for k, v in env.items():
            argv += ["-e", f"{k}={v}"]
        # tail -f /dev/null idles on GNU and BusyBox alike (`sleep infinity` doesn't)
        argv += ["--entrypoint", "/bin/sh", image, "-c", "tail -f /dev/null"]
        rc, out, timed_out, _ = await _run(argv, timeout=self.create_timeout_s)
        if rc != 0:
            await _run(["docker", "rm", "-f", name], timeout=120)   # a timed-out run may have started it
            why = "timed out" if timed_out else f"failed (rc={rc})"
            raise SandboxError(f"docker run {image} {why}: {out.decode(errors='replace')[-2000:]}")
        sb = DockerSandbox(name, image, self.network, self.shell)
        if self.network not in ("none", "host"):
            fmt = "{{(index .NetworkSettings.Networks \"" + self.network + "\").IPAddress}}"
            rc, out, _, _ = await _run(["docker", "inspect", "-f", fmt, name], timeout=60)
            if rc == 0 and out.decode().strip():
                sb.ip = out.decode().strip()
        if limits.disk_gb:
            self._caps[name] = limits.disk_gb * 1e9
            self._start_guard()
        return sb

    # --- disk ----------------------------------------------------------------------------

    async def free_bytes(self) -> int:
        """Free bytes on the fullest disk Docker stores images and layers on."""
        if self._data_dirs is None:
            rc, out, _, _ = await _run(["docker", "info", "--format", "{{.DockerRootDir}}"], timeout=60)
            root = out.decode().strip() if rc == 0 else ""
            # With the containerd image store, layers live under /var/lib/containerd.
            dirs = [d for d in (root, "/var/lib/containerd") if d and os.path.isdir(d)]
            self._data_dirs = dirs or ["/"]
        return min(shutil.disk_usage(d).free for d in self._data_dirs)

    def _start_guard(self) -> None:
        if self._guard is None or self._guard.done():
            self._guard = asyncio.get_running_loop().create_task(self._guard_loop())

    async def _guard_loop(self) -> None:
        while True:
            try:
                await self.check_disk()
            except Exception as e:  # noqa: BLE001 - a watchdog must not die
                logger.warning("disk guard check failed: %s", e)
            await asyncio.sleep(self.guard_interval_s)

    async def check_disk(self) -> list[str]:
        """Kill this run's sandboxes whose writable layer passed their cap; returns their names."""
        rc, out, _, _ = await _run(["docker", "ps", "--size", "--filter", f"label={RUN_KEY}={self.run_id}",
                                    "--format", "{{.Names}}\t{{.Size}}"], timeout=120)
        over = []
        for line in out.decode().splitlines() if rc == 0 else []:
            name, _, size = line.partition("\t")
            cap = self._caps.get(name)
            if cap and name not in self.disk_killed and parse_docker_size(size) > cap:
                over.append(name)
        for name in over:
            logger.warning("disk guard: %s passed %.2f GB, killing it", name, self._caps[name] / 1e9)
            self.disk_killed.add(name)
            await _run(["docker", "kill", name], timeout=60)
        return over

    # --- housekeeping --------------------------------------------------------------------

    async def gc(self) -> int:
        return await gc_docker(self.run_id)

    async def prefetch(self, images: Iterable[str], *, concurrency: int = 4) -> dict[str, float]:
        """Pull the images that aren't local yet. A cached image takes ~0 s."""
        async def one(ref: str) -> None:
            rc, _, _, _ = await _run(["docker", "image", "inspect", ref], timeout=60,
                                     max_output_bytes=1)
            if rc == 0:
                return
            rc, out, timed_out, _ = await _run(["docker", "pull", ref], timeout=3600,
                                               max_output_bytes=100_000)
            if rc != 0 or timed_out:
                raise SandboxError(f"docker pull {ref} failed (rc={rc}): "
                                   f"{out.decode(errors='replace')[-500:]}")
        return await gather_timed(images, one, concurrency)

    async def aclose(self) -> None:
        if self._guard is not None:
            self._guard.cancel()
            self._guard = None
        await super().aclose()


_UNITS = {"B": 1, "kB": 1e3, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}


def parse_docker_size(text: str) -> float:
    """Bytes in a ``docker ps --size`` field like '1.6MB (virtual 1.08GB)' (the writable layer)."""
    m = re.match(r"\s*([\d.]+)\s*([kKMGT]?B)", text or "")
    return float(m.group(1)) * _UNITS[m.group(2)] if m else 0.0


def _parse_created(text: str) -> datetime | None:
    # Docker prints RFC 3339 in UTC with nanoseconds ("2026-09-30T11:02:03.123456789Z").
    try:
        return datetime.strptime(text.strip()[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def gc_docker(run_id: str | None = None, *, older_than: timedelta | None = None) -> int:
    """Remove fleet containers: one run's, or (``run_id=None``) every run's.

    ``older_than`` keeps younger containers, so a reaper can't hit a live run.
    Returns how many were removed.
    """
    label = f"label={RUN_KEY}={run_id}" if run_id else f"label={RUN_KEY}"
    rc, out, _, _ = await _run(["docker", "ps", "-aq", "--filter", label], timeout=60)
    ids = out.decode().split() if rc == 0 else []
    if ids and older_than is not None:
        rc, out, _, _ = await _run(["docker", "inspect", "-f", "{{.Id}} {{.Created}}", *ids], timeout=120)
        cutoff = datetime.now(timezone.utc) - older_than
        ids = []
        for line in out.decode().splitlines() if rc == 0 else []:
            cid, _, created = line.partition(" ")
            ts = _parse_created(created)
            if ts is not None and ts < cutoff:
                ids.append(cid)
    if ids:
        await _run(["docker", "rm", "-f", *ids], timeout=300)
    return len(ids)
