"""Live contract suite for bellhop.fleet: the same checks on every backend.

Skipped by default. Pick the backends to run:

    BELLHOP_DOCKER_LIVE=1 pytest tests/integration_fleet.py -s    # local Docker daemon, free
    MODAL_LIVE=1 pytest tests/integration_fleet.py -s             # Modal sandboxes, ~$0.01

Modal needs the `modal` extra and a token (``modal token new``, or
MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the env). The first Modal run builds
python:3.12-slim, which takes a minute; later runs start in seconds.
"""

import asyncio
import os
import time
import uuid
from datetime import timedelta

import pytest

from bellhop.errors import SandboxError
from bellhop.fleet import TIMEOUT_RC, DockerFleet, Limits, ModalFleet

IMAGE = "python:3.12-slim"
BACKENDS = [b for b, flag in (("docker", "BELLHOP_DOCKER_LIVE"), ("modal", "MODAL_LIVE")) if os.environ.get(flag)]

pytestmark = pytest.mark.skipif(not BACKENDS, reason="set BELLHOP_DOCKER_LIVE=1 and/or MODAL_LIVE=1")


def _fleet(backend: str, **kw):
    run_id = f"live-{backend}-{uuid.uuid4().hex[:6]}"
    limits = Limits(cpu=1, memory_mb=1024)
    if backend == "docker":
        return DockerFleet(run_id, limits=limits, **kw)
    pytest.importorskip("modal")
    return ModalFleet(run_id, limits=limits, max_lifetime=timedelta(minutes=15), **kw)


@pytest.fixture(params=BACKENDS or ["none"])
def backend(request):
    return request.param


def test_exec_contract(backend):
    async def go():
        async with _fleet(backend) as fleet:
            t0 = time.monotonic()
            sb = await fleet.open(IMAGE, env={"GREETING": "hi"}, name_hint="contract")
            print(f"\n[{backend}] open took {time.monotonic() - t0:.1f}s ({sb.id})")

            res = await sb.exec("echo $GREETING; echo oops >&2; pwd; exit 3", workdir="/tmp")
            assert (res.exit_code, res.timed_out, res.truncated) == (3, False, False)
            assert res.output == "hi\noops\n/tmp\n"

            t0 = time.monotonic()
            res = await sb.exec("echo start; sleep 30", timeout=2)
            assert (res.exit_code, res.timed_out) == (TIMEOUT_RC, True)
            assert res.output.startswith("start") and time.monotonic() - t0 < 20

            res = await sb.exec("head -c 200000 /dev/zero | tr '\\0' a", max_output_bytes=1000)
            assert res.exit_code == 0 and len(res.output) == 1000 and res.truncated

            res = await sb.exec("cd /does/not/exist")
            assert res.exit_code != 0 and "does/not/exist" in res.output
    asyncio.run(go())


def test_files(backend):
    async def go():
        async with _fleet(backend) as fleet:
            sb = await fleet.open(IMAGE)
            await sb.write_file("/work/dir/run.sh", "#!/bin/sh\necho ran in $(pwd)\n", executable=True)
            assert await sb.read_file("/work/dir/run.sh", max_bytes=9) == "#!/bin/sh"
            assert (await sb.exec("./run.sh", workdir="/work/dir")).output == "ran in /work/dir\n"
            await sb.write_file("/work/blob.bin", bytes(range(256)) * 64)
            assert (await sb.exec("wc -c < /work/blob.bin")).output.strip() == "16384"
            with pytest.raises(FileNotFoundError):
                await sb.read_file("/no/such/file")
    asyncio.run(go())


def test_network_is_blocked_by_default(backend):
    async def go():
        async with _fleet(backend) as fleet:
            sb = await fleet.open(IMAGE)
            probe = ("python -c \"import urllib.request as u; "
                     "u.urlopen('http://example.com', timeout=5); print('REACHED')\"")
            res = await sb.exec(probe, timeout=30)
            assert res.exit_code != 0 and "REACHED" not in res.output
    asyncio.run(go())


def test_dead_sandbox_is_infra_and_gc_sweeps_the_run(backend):
    async def go():
        async with _fleet(backend) as fleet:
            victim = await fleet.open(IMAGE)
            await victim._teardown()                 # the backend kills it, not the client
            with pytest.raises(SandboxError):
                await victim.exec("echo alive")
            await victim.close()

            leaked = await fleet.open(IMAGE)         # never closed by the caller
            assert await fleet.gc() >= 1
            await asyncio.sleep(2)
            with pytest.raises(SandboxError):
                await leaked.exec("echo alive")
    asyncio.run(go())


def test_max_live_and_prefetch(backend):
    async def go():
        async with _fleet(backend, max_live=1) as fleet:
            timings = await fleet.prefetch([IMAGE])
            print(f"\n[{backend}] prefetch {timings}")
            assert IMAGE in timings
            a = await fleet.open(IMAGE)
            waiter = asyncio.create_task(fleet.open(IMAGE))
            await asyncio.sleep(1)
            assert not waiter.done()
            await a.close()
            b = await asyncio.wait_for(waiter, 300)
            assert (await b.exec("echo ok")).output == "ok\n"
    asyncio.run(go())
