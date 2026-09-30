"""Live end-to-end tests: provision REAL RunPod pods and clusters (costs $).

Skipped by default. Run explicitly with:
    RUNPOD_LIVE=1 pytest tests/integration_live.py -s
(needs RUNPOD_API_KEY and an ~/.ssh/id_ed25519 keypair).

Knobs:
    BELLHOP_LIVE_GCS=gs://bucket/prefix   also exercise the GCS upload leg
                                          (needs gcloud; off by default so CI
                                          runners don't need cloud creds)
    BELLHOP_LIVE_GPU=<alias>              override the call() test's GPU

Stock-outs are skips, not failures: RunPod running dry on a GPU type is not
a bellhop regression, and a suite that fails on capacity noise gets ignored.
"""
import asyncio
import os
import time
from datetime import timedelta

import pytest

from bellhop import PodConfig, ProvisionError, RunSpec, SshProbe, is_capacity_error, run

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUNPOD_LIVE"),
    reason="set RUNPOD_LIVE=1 to run the billed live pod test",
)

_TESTCODE = os.path.join(os.path.dirname(__file__), os.pardir, "_testcode")

# Short stock-out patience: long enough to ride out a blip, short enough that
# a real stock-out still becomes a skip inside the weekly job's 60-min budget
# (the library default is 1 h per box).
LIVE_CAPACITY_WAIT = timedelta(minutes=5)


def _live(coro):
    """asyncio.run, but a capacity-shaped provision failure is a skip."""
    try:
        asyncio.run(coro)
    except ProvisionError as e:
        if is_capacity_error(e):
            pytest.skip(f"RunPod capacity, not a regression: {e}")
        raise


async def _run():
    t0 = time.time()
    spec = RunSpec(
        slug="rpr-selftest",
        codebase=_TESTCODE,
        run="python go.py",
        env={"MY_SECRET": "s3cr3t-xyz"},  # validates env-injection (should appear in out.txt)
        gcs_base=os.environ.get("BELLHOP_LIVE_GCS"),  # upload leg is opt-in
    )
    cfg = PodConfig(
        gpu="RTX4090",   # exercises the canonical-alias path end-to-end
        cloud="COMMUNITY",
        container_disk_gb=20,
        ready=SshProbe("true"),
        provision_timeout=timedelta(seconds=600),
        ready_timeout=timedelta(seconds=600),
        wait_for_capacity=LIVE_CAPACITY_WAIT,
    )
    res = await run(spec, cfg)
    print("=== TEST RESULT ===")
    print("elapsed_s:", round(time.time() - t0))
    print("pod_id:", res.pod_id)
    print("remote_exit:", res.remote_exit)
    print("gcs_uri:", res.gcs_uri)
    print("retrieve:", res.retrieve_cmd)
    print("log_tail:\n" + res.log_tail)
    assert res.remote_exit == 0
    assert "MY_SECRET=s3cr3t-xyz" in res.log_tail  # env-injection worked


def test_live_end_to_end():
    _live(_run())


async def _run_call():
    """call() end-to-end on a real pod: parity pre-flight, cloudpickle
    bootstrap, config.pip deps-on-enter, closure round trip, GPU visibility,
    original-type exception re-raise.

    NB the *client* Python minor version must match the image's (pytorch-cuda
    = py3.11) — run this from a 3.11 venv or the parity pre-flight will
    (correctly) refuse.
    """
    from bellhop import RemoteCallError, pod

    t0 = time.time()
    cfg = PodConfig(
        gpu=os.environ.get("BELLHOP_LIVE_GPU", "RTX4090"),  # override on stock-outs
        cloud="COMMUNITY",
        image_preset="pytorch-cuda",         # py3.11 on the box
        pip=["tqdm"],                        # exercises deps-on-enter
        name="bellhop-call-live",
        provision_timeout=timedelta(seconds=600),
        ready_timeout=timedelta(seconds=600),
        max_lifetime=timedelta(hours=1),     # safety backstop for a ~5min test
        wait_for_capacity=LIVE_CAPACITY_WAIT,
    )
    factor = 3                               # captured by closure

    def compute(xs, scale=1.0):
        import torch
        import tqdm
        return {"sum": sum(xs) * scale * factor,
                "cuda": torch.cuda.is_available(),
                "tqdm": tqdm.__version__}

    def boom():
        raise ValueError("live kaboom")

    async with pod(cfg) as p:
        out = await p.call(compute, [1, 2, 3], scale=2.0)
        print("call result:", out, "| elapsed_s:", round(time.time() - t0))
        assert out["sum"] == 36.0            # args + closure round-tripped
        assert out["cuda"] is True           # really ran on the GPU box
        assert out["tqdm"]                   # config.pip landed before yield
        try:
            await p.call(boom)
            raise AssertionError("expected ValueError from the box")
        except ValueError as e:
            assert isinstance(e.__cause__, RemoteCallError)
            assert "live kaboom" in e.__cause__.remote_traceback
    print("=== CALL LIVE TEST PASSED === total_s:", round(time.time() - t0))


def test_live_call():
    _live(_run_call())


async def _run_slow_boot():
    """The issue-#27 path end-to-end: non-RunPod image + docker_start_cmd sshd
    bootstrap + default TTL (GraphQL create), carried to readiness by the
    docker_start_cmd-widened default windows — no explicit timeouts here on
    purpose; that IS the assertion."""
    from bellhop.pod import pod

    sshd = (
        'apt-get update && apt-get install -y openssh-server && mkdir -p /run/sshd ~/.ssh'
        ' && echo "$PUBLIC_KEY" > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
        " && /usr/sbin/sshd -D"
    )
    cfg = PodConfig(
        gpu="RTX4090",
        image="ubuntu:22.04",
        docker_start_cmd=sshd,
        container_disk_gb=15,
        name="bellhop-live-slowboot",
        wait_for_capacity=LIVE_CAPACITY_WAIT,
    )
    assert cfg.provision_timeout == timedelta(seconds=1200)  # widened default resolved
    assert cfg.has_ttl()  # default timers on -> _gql_create path
    t0 = time.time()
    async with pod(cfg) as p:
        r = await p.exec("echo alive && uname -a")
        print(f"pod {p.id} ready in {time.time() - t0:.0f}s: {r.stdout.strip()}")
        assert r.exit_code == 0
        assert "alive" in r.stdout


def test_live_slow_boot():
    _live(_run_slow_boot())


# One torchrun all-reduce across the two nodes, using only the env bellhop
# injects. It also reports which NCCL transport ran and whether the node has
# RDMA devices, so the test can hold bellhop to the InfiniBand path when it
# should apply.
_CLUSTER_TRAIN = r"""
import json, os, pathlib, torch, torch.distributed as dist
dist.init_process_group("nccl")
rank, world = dist.get_rank(), dist.get_world_size()
t = torch.ones(1 << 20, device=f"cuda:{int(os.environ['LOCAL_RANK'])}")
dist.all_reduce(t)
torch.cuda.synchronize()
ok = bool((t == world).all())
print(f"ALLREDUCE rank={rank} world={world} ok={ok}", flush=True)
if rank == 0:
    pathlib.Path("results").mkdir(exist_ok=True)
    json.dump({"world_size": world, "allreduce_ok": ok,
               "rdma_devices": pathlib.Path("/dev/infiniband").exists(),
               "ib_disabled": os.environ.get("NCCL_IB_DISABLE") == "1"},
              open("results/allreduce.json", "w"))
dist.destroy_process_group()
"""


async def _run_cluster_e2e():
    """run_cluster on a real 2-node Instant Cluster, 1 GPU per node (the
    cheapest shape, ~$7/hr for ~1-2 min). It covers the capacity wait, the
    start-time network check, rank discovery, push to every node, a torchrun
    all-reduce off bellhop's env, the rank-0 pull, and cascade teardown. Weekly
    coverage matters here: the cluster path went untested live for seven weeks
    (Aug 11 to Sep 30) while RunPod's contract drifted underneath it."""
    import dataclasses
    import json
    import tempfile

    from bellhop import ClusterConfig, list_clusters, run_cluster

    t0 = time.time()
    out = tempfile.mkdtemp(prefix="bellhop-live-cluster-")
    with tempfile.TemporaryDirectory() as code:
        with open(os.path.join(code, "train.py"), "w") as f:
            f.write(_CLUSTER_TRAIN)
        spec = RunSpec(
            slug="live-cluster", codebase=code, local_out=out, gcs_base=None,
            env={"NCCL_DEBUG": "INFO"},
            run='torchrun --nnodes "$NUM_NODES" --node_rank "$NODE_RANK" '
                '--nproc_per_node "$NUM_TRAINERS" --rdzv_id live --rdzv_backend static '
                '--rdzv_endpoint "$PRIMARY_ADDR:$PRIMARY_PORT" train.py',
        )
        cfg = ClusterConfig(
            gpu="H100", nodes=2, gpu_count=1, container_disk_gb=20,
            max_hourly_cost=10.0,                 # whole cluster; ~$7/hr at today's minimum
            max_lifetime=timedelta(minutes=30),   # client-side watchdog; clusters have no TTL
            wait_for_capacity=LIVE_CAPACITY_WAIT,
            name="bellhop-live-cluster",
        )
        res = await run_cluster(spec, cfg)
    print("=== CLUSTER RESULT ===")
    print("elapsed_s:", round(time.time() - t0), "cluster:", res.pod_id)
    print("log_tail:\n" + res.log_tail)
    assert res.remote_exit == 0
    facts = json.load(open(os.path.join(out, "results", "allreduce.json")))
    assert facts["world_size"] == 2 and facts["allreduce_ok"]
    log = open(os.path.join(out, "results", "run.log")).read()
    # With bellhop's RDMA setup present, a single-site cluster whose nodes
    # expose RDMA devices must run NCCL over the fabric, not TCP sockets.
    has_rdma_setup = "infiniband" in {f.name for f in dataclasses.fields(ClusterConfig)}
    if has_rdma_setup and facts["rdma_devices"] and not facts["ib_disabled"]:
        assert "Using network IB" in log, "NCCL fell back to TCP sockets"
    # teardown must not leave the (TTL-less) cluster billing
    assert res.pod_id not in {c["id"] for c in await list_clusters()}


def test_live_cluster():
    _live(_run_cluster_e2e())


if __name__ == "__main__":
    asyncio.run(_run())
