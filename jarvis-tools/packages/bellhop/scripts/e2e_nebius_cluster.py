"""Live e2e for the Nebius backend — the acceptance gate before real use.

The Nebius twin of scripts/e2e_cluster.py (which gated the RunPod path):
provision a 2-node 8×B300 cluster on one InfiniBand fabric, push a tiny
codebase, torchrun a 16-way all-reduce using ONLY the env bellhop injects,
pull results from rank 0, verify nothing is left running.

GPU clustering on Nebius requires full 8-GPU nodes (only 8-GPU presets carry
allow_gpu_clustering), so the minimum honest gate is 2×8 — there is no cheap
1-GPU-per-node smoke.

Needs (all env):
  NEBIUS_IAM_TOKEN     auth for the SDK (`nebius iam get-access-token` or SA)
  NEBIUS_PROJECT_ID    parent project (console → project id)
  NEBIUS_FABRIC        InfiniBand fabric for the region, e.g. uk-south1-a
                       (B300); full table: docs.nebius.com GPU clusters page
Optional env:
  NEBIUS_E2E_GPU           default B300
  NEBIUS_E2E_IMAGE_FAMILY  default ubuntu24.04-cuda13.0 (the only CUDA family
                           in uk-south1; older regions have ubuntu22.04-cuda12)

Cost: 16 GPUs for ~20-30 min wall clock — tens of dollars at posted B300
rates. The VM image ships CUDA but not torch; setup pip-installs a cu130
wheel (~3 min).

Run:  uv run python packages/bellhop/scripts/e2e_nebius_cluster.py
"""

import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time
from datetime import timedelta
from uuid import uuid4

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from bellhop import (  # noqa: E402
    ClusterJobError, NebiusClusterConfig, RunSpec, gc_nebius, run_cluster)

TRAIN_PY = r"""
import json, os, pathlib, torch, torch.distributed as dist
from torch.distributed.elastic.multiprocessing.errors import record

@record  # surfaces child tracebacks in the elastic failure summary
def main():
    dist.init_process_group("nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    t = torch.tensor([float(rank)], device=f"cuda:{int(os.environ['LOCAL_RANK'])}")
    dist.all_reduce(t)
    expect = world * (world - 1) / 2
    print(f"rank={rank} sum={t.item()} expect={expect}", flush=True)
    assert t.item() == expect, "all-reduce mismatch"
    if rank == 0:
        pathlib.Path("results").mkdir(exist_ok=True)
        json.dump({"world_size": world, "allreduce_sum": t.item(),
                   "node_rank": os.environ["NODE_RANK"],
                   "primary_addr": os.environ["PRIMARY_ADDR"]},
                  open("results/allreduce.json", "w"))
    dist.destroy_process_group()

main()
"""

# python3 -m, not the torchrun entrypoint: pip --user installs land in
# ~/.local/bin, which is not on the non-interactive ssh PATH.
RUN_CMD = (
    'python3 -m torch.distributed.run --nnodes "$NUM_NODES" '
    '--node_rank "$NODE_RANK" --nproc_per_node "$NUM_TRAINERS" '
    '--rdzv_id e2e --rdzv_backend static '
    '--rdzv_endpoint "$PRIMARY_ADDR:$PRIMARY_PORT" train.py'
)

# The Nebius CUDA VM images ship a bare system python: no pip (unlike the
# RunPod pytorch images). Bootstrap it, then tolerate PEP 668 on noble.
SETUP_PIP = (
    "python3 -m pip --version >/dev/null 2>&1 "
    "|| python3 -m ensurepip --user >/dev/null 2>&1 "
    "|| (sudo apt-get -qq update && sudo apt-get -qq install -y python3-pip)"
)


async def main() -> None:
    for var in ("NEBIUS_IAM_TOKEN", "NEBIUS_PROJECT_ID", "NEBIUS_FABRIC"):
        if not os.environ.get(var):
            sys.exit(f"missing env: {var} (see module docstring)")
    t0 = time.monotonic()
    run_prefix = f"bellhop-e2e-{uuid4().hex[:8]}"   # scope names + gc to THIS run
    with tempfile.TemporaryDirectory() as td:
        (pathlib.Path(td) / "train.py").write_text(TRAIN_PY)
        out = tempfile.mkdtemp(prefix="bellhop-nebius-e2e-")
        gpu = os.environ.get("NEBIUS_E2E_GPU", "B300")
        # Blackwell needs a cu13-built wheel; older SKUs run the default wheel
        # (their cuda12 images predate the cu130 driver floor).
        torch_pkg = ("torch --index-url https://download.pytorch.org/whl/cu130"
                     if gpu.upper().startswith("B") else "torch")
        spec = RunSpec(
            slug="nebius-cluster-e2e", codebase=td, run=RUN_CMD,
            setup=(f"{SETUP_PIP} && export PIP_BREAK_SYSTEM_PACKAGES=1 && "
                   "python3 -m pip install -q --user numpy && "
                   f"python3 -m pip install -q --user {torch_pkg}"),
            results_subdir="results", local_out=out, gcs_base=None)
        config = NebiusClusterConfig(
            fabric=os.environ["NEBIUS_FABRIC"],
            gpu=gpu, nodes=2, gpu_count=8,
            image_family=os.environ.get("NEBIUS_E2E_IMAGE_FAMILY",
                                        "ubuntu24.04-cuda13.0"),
            boot_disk_gb=200, max_lifetime=timedelta(hours=1),
            name=run_prefix,
        )
        try:
            res = await run_cluster(spec, config)
        except ClusterJobError as e:
            print("\nexec failed; per-rank output tails:", flush=True)
            for r in sorted(e.results):
                rr = e.results[r]
                if rr is None:
                    print(f"--- rank {r}: cancelled / no result")
                    continue
                print(f"--- rank {r} exit={rr.exit_code}\n"
                      f"[stdout]\n{rr.stdout[-6000:]}\n"
                      f"[stderr]\n{rr.stderr[-6000:]}", flush=True)
            raise
        print(f"\nrun_cluster returned: cluster={res.pod_id} exit={res.remote_exit} "
              f"({time.monotonic()-t0:.0f}s)")
        print("log tail:\n" + res.log_tail)
        payload = json.load(open(pathlib.Path(res.local_results) / "results" / "allreduce.json"))
        print("pulled results/allreduce.json:", payload)
        world = config.nodes * config.gpu_count
        assert payload["world_size"] == world
        assert payload["allreduce_sum"] == world * (world - 1) / 2

    leftover = await gc_nebius(timedelta(seconds=0), name_prefix=run_prefix, dry_run=True)
    print("this run's resources remaining:", leftover or "none")
    assert not leftover, "teardown left resources behind!"
    print(f"\nE2E PASSED in {time.monotonic()-t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
