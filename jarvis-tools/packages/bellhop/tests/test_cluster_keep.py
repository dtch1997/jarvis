"""Offline tests for multi-node failure handling: keep policy, salvage, errors."""

import asyncio
import contextlib
import importlib
from pathlib import Path

import pytest

from bellhop import ClusterConfig, ClusterJobError, PodNotReadyError, PreflightError, RunSpec
from bellhop.backend import ExecResult
from bellhop.cli import main as cli_main
from bellhop.cluster import Cluster
from bellhop.errors import ExecTimeoutError

# the package re-exports functions named cluster/pod, which shadow the submodules
cluster_mod = importlib.import_module("bellhop.cluster")
pod_mod = importlib.import_module("bellhop.pod")

IPS = {0: "10.65.0.2", 1: "10.65.0.3"}


# ---- errors carry the evidence ------------------------------------------------

def test_cluster_job_error_message_ends_with_the_failing_ranks_output():
    results = {0: None, 1: ExecResult(1, "loading shards\nRuntimeError: CUDA out of memory\n", "")}
    e = ClusterJobError("exec_all failed on cluster c1", results=results)
    assert "failed ranks: [1]" in str(e)
    assert "rank 1 output" in str(e) and "CUDA out of memory" in str(e)
    assert e.remote_exit == 1 and "CUDA out of memory" in e.log_tail


# ---- exec_all never leaves sibling ranks running -------------------------------------

class _Hang:
    def __init__(self):
        self.cancelled = False

    async def exec(self, cmd, env=None, timeout=None):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _TimesOut:
    async def exec(self, cmd, env=None, timeout=None):
        raise ExecTimeoutError("exec timed out after 5s")


class _Cfg:
    gpu_count = 1


def _with_cfg(node):
    node.config = _Cfg()
    return node


def test_a_timeout_on_one_rank_cancels_the_others():
    hang = _with_cfg(_Hang())
    clu = Cluster("c1", [_with_cfg(_TimesOut()), hang], dict(IPS))
    with pytest.raises(ExecTimeoutError):
        asyncio.run(clu.exec_all("train", timeout=5))
    assert hang.cancelled


def test_a_cancelled_exec_kills_its_ssh_client():
    async def go():
        proc = await asyncio.create_subprocess_exec(
            "sleep", "30", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        task = asyncio.create_task(pod_mod._communicate(proc, timeout=None))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return proc.returncode

    rc = asyncio.run(go())
    assert rc is not None and rc != 0          # killed, not left running


# ---- cluster(): keep policy ---------------------------------------------------------

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

    def deleted(self):
        return any("deleteCluster" in q for q in self.posts)


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

    async def _noop(self):
        return None

    async def _exec(self, cmd, env=None, timeout=None):
        rank = {"p0": 0, "p1": 1}[self.id]
        return ExecResult(0, f"NODE_RANK={rank}\nNODE_ADDR=10.65.0.{rank + 2}/24\n", "")

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(cluster_mod, "RunpodGraphQL", _gql)
    monkeypatch.setattr(cluster_mod, "RunpodRest", _Rest)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_provision", _noop)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_ready", _noop)
    monkeypatch.setattr(cluster_mod.Pod, "exec", _exec)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)      # _delete_cluster's cascade settle
    return gqls


def _run_ctx(cfg, keep, body_raises=False, hold=None):
    async def go():
        async with cluster_mod.cluster(cfg, keep=keep, api_key="k") as clu:
            if hold:
                clu.hold(hold)
            if body_raises:
                raise RuntimeError("job failed")

    if body_raises:
        with pytest.raises(RuntimeError, match="job failed"):
            asyncio.run(go())
    else:
        asyncio.run(go())


@pytest.mark.parametrize("keep, body_raises, deleted", [
    (False, True, True),
    (False, False, True),
    ("on-failure", True, False),        # the point: a failed job's nodes survive
    ("on-failure", False, True),
    (True, False, False),
    (True, True, False),
])
def test_keep_policy_matrix(tmp_path, fake_runpod, capsys, keep, body_raises, deleted):
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))
    _run_ctx(cfg, keep, body_raises)
    assert fake_runpod[0].deleted() is deleted
    err = capsys.readouterr().err
    if not deleted:
        assert "cluster c1 KEPT" in err and "bellhop clusters delete c1" in err
        assert "no server-side" in err


def test_held_cluster_survives_keep_false(tmp_path, fake_runpod, capsys):
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))
    _run_ctx(cfg, False, hold="salvage of rank 1 /workspace/x failed")
    assert not fake_runpod[0].deleted()
    assert "salvage of rank 1" in capsys.readouterr().err


def test_a_failed_start_is_deleted_even_with_keep_on_failure(tmp_path, fake_runpod, monkeypatch):
    async def _discover(pods):
        raise PodNotReadyError("pod p1 did not expose NODE_RANK")

    monkeypatch.setattr(cluster_mod, "_discover_ranks", _discover)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))

    async def go():
        async with cluster_mod.cluster(cfg, keep="on-failure", api_key="k"):
            raise AssertionError("unreachable")

    with pytest.raises(PodNotReadyError):
        asyncio.run(go())
    assert fake_runpod[0].deleted()          # nothing on it worth paying for


def test_bad_keep_value_fails_before_spending(tmp_path, fake_runpod):
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))
    with pytest.raises(PreflightError, match="keep must be"):
        _run_ctx(cfg, "sometimes")
    assert fake_runpod == []                  # no GraphQL client was even built


# ---- run_cluster(): salvage on failure ------------------------------------------------

class _Node:
    """A rank whose job can fail, with a set of files that 'exist' on it."""

    def __init__(self, rank, files, fail=False, pull_raises=False):
        self.id = f"p{rank}"
        self.rank, self.files, self.fail, self.pull_raises = rank, set(files), fail, pull_raises
        self.pulled: list[tuple[str, str]] = []
        self.config = _Cfg()

    async def exec(self, cmd, env=None, timeout=None):
        if "--- run ---" in cmd and self.fail:
            return ExecResult(1, "--- run ---\nValueError: bad batch\n", "")
        return ExecResult(0, "", "")

    async def push(self, local, remote):
        return None

    async def exists_remote(self, path):
        return path in self.files

    async def pull(self, remote, dest):
        if self.pull_raises:
            raise RuntimeError("ssh: connection reset")
        self.pulled.append((remote, str(dest)))


def _fake_cluster_ctx(monkeypatch, nodes):
    seen = {}

    @contextlib.asynccontextmanager
    async def _ctx(config, *, keep=False, api_key=None):
        seen["keep"] = keep
        clu = Cluster("c1", nodes, dict(IPS))
        seen["clu"] = clu
        yield clu

    monkeypatch.setattr(cluster_mod, "cluster", _ctx)
    return seen


def test_run_cluster_salvages_every_rank_then_raises(tmp_path, monkeypatch):
    code = tmp_path / "code"
    code.mkdir()
    out = tmp_path / "out"
    run_dir = "/workspace/job"
    nodes = [
        _Node(0, {f"{run_dir}/results", f"{run_dir}/ckpt"}),
        _Node(1, {f"{run_dir}/results"}, fail=True),
    ]
    seen = _fake_cluster_ctx(monkeypatch, nodes)
    spec = RunSpec(slug="job", codebase=str(code), run="torchrun train.py",
                   salvage=["ckpt"], local_out=str(out), gcs_base=None)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))

    with pytest.raises(ClusterJobError, match="ValueError: bad batch"):
        asyncio.run(cluster_mod.run_cluster(spec, cfg, keep="on-failure"))

    assert seen["keep"] == "on-failure"                        # forwarded to the cluster
    assert nodes[0].pulled == [(f"{run_dir}/results", str(out)),        # rank 0 -> local_out
                               (f"{run_dir}/ckpt", str(out))]
    assert nodes[1].pulled == [(f"{run_dir}/results", str(Path(out) / "rank1"))]
    assert seen["clu"].hold_reason is None


def test_run_cluster_holds_the_cluster_when_salvage_fails(tmp_path, monkeypatch):
    code = tmp_path / "code"
    code.mkdir()
    run_dir = "/workspace/job"
    nodes = [_Node(0, {f"{run_dir}/results"}, fail=True, pull_raises=True),
             _Node(1, set())]
    seen = _fake_cluster_ctx(monkeypatch, nodes)
    spec = RunSpec(slug="job", codebase=str(code), run="torchrun train.py",
                   local_out=str(tmp_path / "out"), gcs_base=None)
    cfg = ClusterConfig(gpu="NVIDIA H100 80GB HBM3", ssh_key=_key(tmp_path))

    with pytest.raises(ClusterJobError):
        asyncio.run(cluster_mod.run_cluster(spec, cfg))
    assert "salvage of rank 0" in seen["clu"].hold_reason


# ---- deleting one cluster ----------------------------------------------------------------

def test_cli_clusters_delete(monkeypatch, capsys):
    calls = []

    async def _delete(cluster_id, *, api_key=None):
        calls.append(cluster_id)

    monkeypatch.setattr(cluster_mod, "delete_cluster", _delete)
    assert cli_main(["clusters", "delete", "c123"]) == 0
    assert calls == ["c123"] and "deleted cluster c123" in capsys.readouterr().out


def test_delete_cluster_by_id(monkeypatch):
    removed = []

    class _ListingGql:
        def __init__(self, api_key=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def _post(self, query, variables):
            return {"myself": {"clusters": [{"id": "c1", "pods": [{"id": "p0"}, {"id": "p1"}]}]}}

    class _RestCM(_Rest):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

    async def _fake_delete(gql, rest, cid, pod_ids):
        removed.append((cid, pod_ids))

    monkeypatch.setattr(cluster_mod, "RunpodGraphQL", _ListingGql)
    monkeypatch.setattr(cluster_mod, "RunpodRest", _RestCM)
    monkeypatch.setattr(cluster_mod, "_delete_cluster", _fake_delete)
    asyncio.run(cluster_mod.delete_cluster("c1", api_key="k"))
    assert removed == [("c1", ["p0", "p1"])]
    with pytest.raises(PreflightError, match="no cluster 'nope'"):
        asyncio.run(cluster_mod.delete_cluster("nope", api_key="k"))


# ---- Nebius honors the same policy ----------------------------------------------------------

@pytest.mark.parametrize("keep, deleted", [("on-failure", False), (False, True)])
def test_nebius_keep_on_failure(tmp_path, capsys, keep, deleted):
    from test_nebius_offline import _cfg as nebius_cfg
    from test_nebius_offline import _FakeApi

    from bellhop import nebius_cluster

    api = _FakeApi()

    async def go():
        async with nebius_cluster(nebius_cfg(tmp_path, nodes=2), keep=keep, _api=api):
            raise RuntimeError("job failed")

    with pytest.raises(RuntimeError):
        asyncio.run(go())
    assert bool(api.deleted["instances"]) is deleted
    if not deleted:
        assert "nebius cluster gpucluster-0 KEPT" in capsys.readouterr().err
