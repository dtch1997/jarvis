"""Sandbox fleets: many short-lived, isolated containers for code you don't trust.

A fleet hands out sandboxes for one run. Each sandbox starts from any image,
runs commands, and is destroyed after one unit of work, such as an RL rollout
or a grading job. bellhop's boxes (``pod()``, ``sandbox()``, ``cluster()``)
run *your* code; a fleet runs the agent's.

    from bellhop.fleet import Limits, ModalFleet

    async with ModalFleet(run_id="r1", limits=Limits(cpu=1, memory_mb=2048), max_live=64) as fleet:
        sb = await fleet.open("python:3.12-slim")
        res = await sb.exec("python -c 'print(1 + 1)'", workdir="/tmp", timeout=30)
        assert res.output == "2\\n" and res.exit_code == 0
        await sb.close()

Two backends share the contract (docs/design/sandbox-fleet.md):

- :class:`DockerFleet` runs containers on the local Docker daemon.
- :class:`ModalFleet` runs Modal Sandboxes (gVisor). Any machine with a Modal
  token can reach them, including a RunPod pod, which can't run Docker itself.

``bellhop.Sandbox`` is the Modal *job box*; ``bellhop.fleet.Sandbox`` is the
per-rollout protocol here.
"""

from __future__ import annotations

from ..errors import SandboxError
from .base import CLIENT_GRACE_S, RUN_KEY, TIMEOUT_RC, CommandResult, Fleet, Limits, Sandbox
from .docker import DockerFleet, DockerSandbox, gc_docker, parse_docker_size
from .modal import ModalFleet, ModalSandbox, gc_modal

BACKENDS = {"docker": DockerFleet, "modal": ModalFleet}


def make_fleet(backend: str, run_id: str | None = None, **kwargs) -> Fleet:
    """Build a fleet from a backend name ("docker" or "modal"), e.g. from a run config."""
    try:
        cls = BACKENDS[backend]
    except KeyError:
        from ..errors import PreflightError
        raise PreflightError(f"unknown fleet backend {backend!r} (have {sorted(BACKENDS)})") from None
    return cls(run_id, **kwargs)


__all__ = [
    "Fleet", "Sandbox", "Limits", "CommandResult", "SandboxError", "make_fleet", "BACKENDS",
    "DockerFleet", "DockerSandbox", "gc_docker", "parse_docker_size",
    "ModalFleet", "ModalSandbox", "gc_modal",
    "TIMEOUT_RC", "CLIENT_GRACE_S", "RUN_KEY",
]
