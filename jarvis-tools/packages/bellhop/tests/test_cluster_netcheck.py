"""Offline tests for the start-time cluster network check and data-center record."""

import asyncio
import importlib
import os
import shutil
import subprocess
from datetime import timedelta

import pytest

from bellhop import ClusterConfig, PodNotReadyError
from bellhop.backend import ExecResult
from bellhop.cluster import _NETCHECK, Cluster

# the package re-exports a function named cluster, which shadows the submodule
cluster_mod = importlib.import_module("bellhop.cluster")

IPS = {0: "10.65.0.2", 1: "10.65.0.3", 2: "10.65.0.4"}


class _Node:
    def __init__(self, pod_id, result=ExecResult(0, "", "")):
        self.id = pod_id
        self.result = result
        self.env = None

    async def exec(self, cmd, env=None, timeout=None):
        self.env = env
        return self.result


def _cluster(results=None):
    results = results or {}
    nodes = [_Node(f"p{r}", results.get(r, ExecResult(0, "", ""))) for r in IPS]
    return Cluster("cid", nodes, dict(IPS)), nodes


def test_every_rank_probes_all_peers_but_itself():
    clu, nodes = _cluster()
    asyncio.run(clu.check_network(timeout=30))
    for rank, node in enumerate(nodes):
        peers = node.env["BELLHOP_PEERS"].split()
        assert sorted(peers) == sorted(ip for r, ip in IPS.items() if r != rank)
        assert node.env["BELLHOP_NETCHECK_TIMEOUT"] == "30"


def test_unreachable_pairs_are_named():
    bad = ExecResult(3, "REACHABLE 10.65.0.4\nUNREACHABLE 10.65.0.2 No route to host (rc=1)\n", "")
    clu, _ = _cluster({1: bad})
    with pytest.raises(PodNotReadyError) as ei:
        asyncio.run(clu.check_network(timeout=30))
    msg = str(ei.value)
    assert "rank 1 -> 10.65.0.2 No route to host" in msg
    assert "10.65.0.4" not in msg                     # the reachable peer isn't blamed


def test_a_check_that_cannot_even_run_is_reported():
    broken = ExecResult(255, "", "ssh: connect to host 1.2.3.4 port 22: Connection timed out")
    clu, _ = _cluster({2: broken})
    with pytest.raises(PodNotReadyError, match="rank 2: check exited 255: ssh: connect"):
        asyncio.run(clu.check_network(timeout=30))


@pytest.mark.skipif(not (shutil.which("bash") and shutil.which("timeout")),
                    reason="needs bash + coreutils timeout")
def test_probe_script_itself(tmp_path):
    """Run the real bash probe locally: loopback answers (open or refused);
    TEST-NET-1 (192.0.2.1, never routed) must come back UNREACHABLE."""
    def run(peers):
        env = {**os.environ, "BELLHOP_PEERS": peers, "BELLHOP_NETCHECK_TIMEOUT": "1",
               "BELLHOP_PROBE_TIMEOUT": "1"}
        return subprocess.run(["bash", "-c", _NETCHECK], env=env, capture_output=True,
                              text=True, timeout=60)

    ok = run("127.0.0.1")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "REACHABLE 127.0.0.1" in ok.stdout
    bad = run("127.0.0.1 192.0.2.1")
    assert bad.returncode == 3, bad.stdout + bad.stderr
    assert "UNREACHABLE 192.0.2.1" in bad.stdout
    assert "UNREACHABLE 127.0.0.1" not in bad.stdout


# ---- data centers --------------------------------------------------------------

def test_split_cluster_warns(capsys):
    clu = Cluster("cid", [], {}, data_centers={0: "AP-IN-1", 1: "AP-IN-2"})
    clu.warn_if_split()
    err = capsys.readouterr().err
    assert "spans data centers" in err and "AP-IN-1" in err and "AP-IN-2" in err


@pytest.mark.parametrize("dcs", [{0: "EUR-IS-3", 1: "EUR-IS-3"}, {0: None, 1: None}, {}])
def test_single_site_or_unknown_is_quiet(capsys, dcs):
    Cluster("cid", [], {}, data_centers=dcs).warn_if_split()
    assert capsys.readouterr().err == ""


# ---- cluster(): the check is part of start -----------------------------------------

def _key(tmp_path):
    key = tmp_path / "id"
    key.write_text("x")
    (tmp_path / "id.pub").write_text("ssh-ed25519 AAAA test")
    return str(key)


class _Gql:
    def __init__(self, api_key=None):
        self.posts = []

    async def _post(self, query, variables):
        self.posts.append(query)
        if "createCluster" in query:
            if "deployCost" not in variables["input"]:
                raise cluster_mod.ProvisionError("graphql error: ... minimum price (3.49) ...")
            return {"createCluster": {"id": "c1", "pods": [{"id": "p0"}, {"id": "p1"}]}}
        return {"deleteCluster": True}

    async def aclose(self):
        return None


class _Rest:
    def __init__(self, api_key=None):
        pass

    async def get_pod(self, pid):
        raise RuntimeError("404")

    async def delete_pod(self, pid):
        return None

    async def aclose(self):
        return None


@pytest.fixture
def fake_runpod(monkeypatch):
    gqls = []

    def _gql(api_key=None):
        gqls.append(_Gql())
        return gqls[-1]

    async def _provisioned(self):
        self._meta = {"machine": {"dataCenterId": {"p0": "AP-IN-1", "p1": "AP-IN-2"}[self.id]}}

    async def _ready(self):
        return None

    async def _exec(self, cmd, env=None, timeout=None):
        rank = {"p0": 0, "p1": 1}[self.id]
        return ExecResult(0, f"NODE_RANK={rank}\nNODE_ADDR=10.65.0.{rank + 2}/24\n", "")

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(cluster_mod, "RunpodGraphQL", _gql)
    monkeypatch.setattr(cluster_mod, "RunpodRest", _Rest)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_provision", _provisioned)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_ready", _ready)
    monkeypatch.setattr(cluster_mod.Pod, "exec", _exec)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)       # _delete_cluster's cascade settle
    return gqls


def test_cluster_start_checks_network_and_records_sites(tmp_path, fake_runpod, monkeypatch, capsys):
    seen = {}

    async def _check(self, timeout=120.0):
        seen["timeout"] = timeout

    monkeypatch.setattr(Cluster, "check_network", _check)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path),
                        network_check_timeout=timedelta(seconds=45))

    async def go():
        async with cluster_mod.cluster(cfg, api_key="k") as clu:
            return clu.data_centers

    assert asyncio.run(go()) == {0: "AP-IN-1", 1: "AP-IN-2"}
    assert seen["timeout"] == 45
    assert "spans data centers" in capsys.readouterr().err


def test_failed_network_check_tears_the_cluster_down(tmp_path, fake_runpod, monkeypatch):
    async def _check(self, timeout=120.0):
        raise PodNotReadyError("overlay network not routable")

    monkeypatch.setattr(Cluster, "check_network", _check)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))

    async def go():
        async with cluster_mod.cluster(cfg, api_key="k"):
            raise AssertionError("must not yield a cluster that failed its network check")

    with pytest.raises(PodNotReadyError, match="not routable"):
        asyncio.run(go())
    assert any("deleteCluster" in q for q in fake_runpod[0].posts)


def test_network_check_can_be_skipped(tmp_path, fake_runpod, monkeypatch):
    async def _check(self, timeout=120.0):
        raise AssertionError("check must not run when network_check_timeout=None")

    monkeypatch.setattr(Cluster, "check_network", _check)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path),
                        network_check_timeout=None)

    async def go():
        async with cluster_mod.cluster(cfg, api_key="k") as clu:
            return clu.id

    assert asyncio.run(go()) == "c1"


def test_nebius_cluster_runs_the_same_check(tmp_path, monkeypatch):
    from test_nebius_offline import _cfg as nebius_cfg
    from test_nebius_offline import _FakeApi

    from bellhop import nebius_cluster

    calls = []

    async def _check(self, timeout=120.0):
        calls.append((self.id, timeout))

    monkeypatch.setattr(Cluster, "check_network", _check)
    api = _FakeApi()

    async def go():
        cfg = nebius_cfg(tmp_path, nodes=2, network_check_timeout=timedelta(seconds=30))
        async with nebius_cluster(cfg, _api=api):
            pass

    asyncio.run(go())
    assert calls == [("gpucluster-0", 30)]
