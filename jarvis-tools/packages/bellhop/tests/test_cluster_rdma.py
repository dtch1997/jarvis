"""Offline tests for NCCL transport setup on RunPod clusters (RDMA prep + env)."""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from bellhop import ClusterConfig
from bellhop.backend import ExecResult
from bellhop.cluster import _NCCL_PREP, Cluster, _choose_transport, _prepare_nccl

IPS = {0: "10.65.0.2", 1: "10.65.0.3"}
ROCE_ENV = ("ENV NCCL_IB_DISABLE=0\nENV NCCL_IB_GID_INDEX=7\n"
            "ENV NCCL_IB_HCA=mlx5_0,mlx5_1\nENV NCCL_SOCKET_IFNAME=ens1,ens2\n")


class _Cfg:
    gpu_count = 8


class _Node:
    def __init__(self, stdout, exit_code=0):
        self.stdout, self.exit_code = stdout, exit_code
        self.env = None
        self.config = _Cfg()

    async def exec(self, cmd, env=None, timeout=None):
        self.env = env
        return ExecResult(self.exit_code, self.stdout, "")


def _cfg(**kw):
    return ClusterConfig(gpu="H200", **kw)


# ---- the prep step --------------------------------------------------------------

def test_prepare_parses_provider_env_and_rdma_status():
    nodes = [_Node(ROCE_ENV + "RDMA installed\n"), _Node("RDMA no-devices\n")]
    penv, rdma = asyncio.run(_prepare_nccl(nodes, install=True))
    assert penv[0] == {"NCCL_IB_DISABLE": "0", "NCCL_IB_GID_INDEX": "7",
                       "NCCL_IB_HCA": "mlx5_0,mlx5_1", "NCCL_SOCKET_IFNAME": "ens1,ens2"}
    assert penv[1] == {}
    assert rdma == {0: "installed", 1: "no-devices"}
    assert nodes[0].env == {"BELLHOP_RDMA_INSTALL": "1"}


def test_prepare_without_install_says_so():
    nodes = [_Node("RDMA libs-missing\n")]
    _, rdma = asyncio.run(_prepare_nccl(nodes, install=False))
    assert rdma == {0: "libs-missing"}
    assert nodes[0].env == {"BELLHOP_RDMA_INSTALL": "0"}


@pytest.mark.skipif(not shutil.which("bash") or Path("/dev/infiniband").exists(),
                    reason="needs bash, and a host without RDMA devices")
def test_prep_script_itself_on_a_host_without_rdma():
    env = {**os.environ, "BELLHOP_RDMA_INSTALL": "1"}
    res = subprocess.run(["bash", "-c", _NCCL_PREP], env=env, capture_output=True,
                         text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert "RDMA no-devices" in res.stdout            # never tries to apt-install here
    assert "NCCL_VERSION" not in res.stdout


# ---- rank env layering --------------------------------------------------------------

def test_provider_nccl_env_rides_under_bellhops_rendezvous():
    clu = Cluster("c1", [_Node(""), _Node("")], dict(IPS),
                  provider_env={0: {"NCCL_IB_HCA": "mlx5_0", "NCCL_SOCKET_IFNAME": "ens1,ens2"}})
    env = clu.rank_env(0)
    assert env["NCCL_IB_HCA"] == "mlx5_0"
    assert env["NCCL_SOCKET_IFNAME"] == "ens1,ens2"   # RunPod's NIC list beats the default
    assert env["MASTER_ADDR"] == "10.65.0.2" and env["MASTER_PORT"] == "29500"
    assert clu.rank_env(1)["NCCL_SOCKET_IFNAME"] == "ens1"   # no provider env -> default
    assert "NCCL_IB_DISABLE" not in clu.rank_env(1)


def test_disabling_ib_overrides_the_provider():
    clu = Cluster("c1", [_Node("")], {0: "10.65.0.2"},
                  provider_env={0: {"NCCL_IB_DISABLE": "0"}})
    clu.disable_ib("nodes span data centers")
    assert clu.rank_env(0)["NCCL_IB_DISABLE"] == "1"
    assert clu.ib_disabled == "nodes span data centers"


# ---- choosing the transport ------------------------------------------------------------

def _clu(dcs):
    return Cluster("c1", [_Node(""), _Node("")], dict(IPS), data_centers=dcs)


def test_same_site_with_rdma_keeps_ib(capsys):
    clu = _clu({0: "EUR-IS-3", 1: "EUR-IS-3"})
    _choose_transport(clu, _cfg(), {0: "installed", 1: "ready"})
    assert clu.ib_disabled is None
    assert capsys.readouterr().err == ""


def test_split_sites_force_sockets(capsys):
    clu = _clu({0: "AP-IN-1", 1: "AP-IN-2"})
    _choose_transport(clu, _cfg(), {0: "installed", 1: "installed"})
    assert clu.ib_disabled == "nodes span data centers"
    assert "data_center_id" in capsys.readouterr().err


def test_infiniband_false_forces_sockets_quietly(capsys):
    clu = _clu({0: "EUR-IS-3", 1: "EUR-IS-3"})
    _choose_transport(clu, _cfg(infiniband=False), {0: "libs-missing", 1: "libs-missing"})
    assert clu.rank_env(0)["NCCL_IB_DISABLE"] == "1"
    assert capsys.readouterr().err == ""               # asked for it; nothing to warn about


def test_missing_rdma_is_announced(capsys):
    clu = _clu({0: "US-KS-2", 1: "US-KS-2"})
    _choose_transport(clu, _cfg(), {0: "no-devices", 1: "install-failed: E: Unable to locate"})
    err = capsys.readouterr().err
    assert "no usable RDMA" in err and "rank 1: install-failed" in err
    assert clu.ib_disabled is None                     # NCCL falls back by itself
