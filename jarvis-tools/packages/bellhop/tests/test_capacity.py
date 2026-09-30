"""Offline tests for waiting out stock-outs (bellhop.capacity + its call sites)."""

import asyncio
import importlib
from datetime import timedelta

import pytest

from bellhop import (
    Backoff,
    CapacityError,
    CapacityTimeoutError,
    ClusterConfig,
    PodConfig,
    ProvisionError,
    is_capacity_error,
    wait_for_capacity,
)
from bellhop.backend import ExecResult

# the package re-exports functions named pod/cluster, which shadow the submodules
capacity = importlib.import_module("bellhop.capacity")
cluster_mod = importlib.import_module("bellhop.cluster")
pod_mod = importlib.import_module("bellhop.pod")

NO_JITTER = Backoff(jitter=0.0)


class _Clock:
    """Fake monotonic clock + sleep: sleeping advances time instantly."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self):
        return self.now

    async def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


@pytest.fixture
def fake_time(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(capacity, "_clock", c.clock)
    monkeypatch.setattr(capacity, "_sleep", c.sleep)
    return c


def _scripted(outcomes):
    """An attempt() that raises/returns the scripted outcomes in order."""
    calls = []

    async def attempt():
        calls.append(len(calls))
        item = outcomes.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item
    attempt.calls = calls
    return attempt


# ---- the primitive ------------------------------------------------------------

def test_backoff_schedule_doubles_then_caps():
    assert [NO_JITTER.delay(n) for n in range(1, 7)] == [15, 30, 60, 120, 120, 120]


def test_backoff_jitter_stays_in_band():
    b = Backoff(initial=100, jitter=0.2, max=1000)
    assert all(80 <= b.delay(1) <= 120 for _ in range(200))


def test_success_first_try_never_sleeps(fake_time):
    attempt = _scripted(["box"])
    assert asyncio.run(wait_for_capacity(attempt, timeout=timedelta(hours=1))) == "box"
    assert fake_time.sleeps == []


def test_retries_stockouts_with_backoff_then_succeeds(fake_time, capsys):
    attempt = _scripted([CapacityError("no stock"), CapacityError("no stock"), "box"])
    out = asyncio.run(wait_for_capacity(attempt, timeout=timedelta(hours=1),
                                        what="2x8 H200 cluster", backoff=NO_JITTER))
    assert out == "box"
    assert fake_time.sleeps == [15, 30]
    err = capsys.readouterr().err
    assert "2x8 H200 cluster" in err
    assert err.count("wait_for_capacity=None") == 1        # opt-out hint once, not per retry


def test_gives_up_at_the_deadline_with_a_typed_error(fake_time):
    attempt = _scripted([CapacityError("no stock")] * 50)
    with pytest.raises(CapacityTimeoutError) as ei:
        asyncio.run(wait_for_capacity(attempt, timeout=timedelta(minutes=3), backoff=NO_JITTER))
    # 15 + 30 + 60 = 105s, then the last pause is clipped to the 75s left
    assert fake_time.sleeps == [15, 30, 60, 75]
    assert len(attempt.calls) == 5                            # one final try AT the deadline
    assert isinstance(ei.value.__cause__, CapacityError)
    assert is_capacity_error(ei.value)                        # live-suite skip logic still sees it
    assert isinstance(ei.value, ProvisionError)               # old handlers still catch it


def test_other_errors_propagate_immediately(fake_time):
    attempt = _scripted([ProvisionError("bad image")])
    with pytest.raises(ProvisionError, match="bad image"):
        asyncio.run(wait_for_capacity(attempt, timeout=timedelta(hours=1)))
    assert fake_time.sleeps == [] and len(attempt.calls) == 1


@pytest.mark.parametrize("timeout", [None, timedelta(0)])
def test_opt_out_is_a_single_attempt(fake_time, timeout):
    attempt = _scripted([CapacityError("no stock")])
    with pytest.raises(CapacityError) as ei:
        asyncio.run(wait_for_capacity(attempt, timeout=timeout))
    assert not isinstance(ei.value, CapacityTimeoutError)    # the raw stock-out, untouched
    assert fake_time.sleeps == []


def test_default_predicate_also_accepts_capacity_prose(fake_time):
    # external callers may raise plain ProvisionErrors carrying RunPod's prose
    attempt = _scripted([ProvisionError("graphql error: Insufficient resources"), "ok"])
    assert asyncio.run(wait_for_capacity(attempt, timeout=timedelta(hours=1))) == "ok"


# ---- pod create paths classify stock-outs precisely -------------------------------

def _key(tmp_path):
    key = tmp_path / "id"
    key.write_text("x")
    (tmp_path / "id.pub").write_text("ssh-ed25519 AAAA test")
    return str(key)


class _FakeGqlClient:
    """Stand-in for RunpodGraphQL inside _gql_create (async CM + scripted creates)."""

    replies: list = []

    def __init__(self, api_key=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def create_pod_on_demand(self, gi):
        item = type(self).replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def test_gql_create_all_stockouts_is_capacity(tmp_path, monkeypatch):
    _FakeGqlClient.replies = [
        ProvisionError("podFindAndDeployOnDemand returned null (no capacity for the request)"),
        ProvisionError("graphql error: This machine does not have the resources"),
    ]
    monkeypatch.setattr(pod_mod, "RunpodGraphQL", _FakeGqlClient)
    cfg = PodConfig(gpu="H200", ssh_key=_key(tmp_path))          # COMMUNITY -> SECURE
    with pytest.raises(CapacityError):
        asyncio.run(pod_mod._gql_create(cfg, api_key="k"))


def test_gql_create_mixed_failure_is_not_capacity(tmp_path, monkeypatch):
    _FakeGqlClient.replies = [
        ProvisionError("podFindAndDeployOnDemand returned null (no capacity for the request)"),
        ProvisionError("graphql error: image not found"),
    ]
    monkeypatch.setattr(pod_mod, "RunpodGraphQL", _FakeGqlClient)
    cfg = PodConfig(gpu="H200", ssh_key=_key(tmp_path))
    with pytest.raises(ProvisionError) as ei:
        asyncio.run(pod_mod._gql_create(cfg, api_key="k"))
    assert not isinstance(ei.value, CapacityError)            # a broken request must not be waited on


class _FakeRest:
    def __init__(self, replies):
        self.replies = list(replies)
        self.bodies = []
        self.deleted = []

    async def create_pod(self, body):
        self.bodies.append(dict(body))
        item = self.replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def delete_pod(self, pid):
        self.deleted.append(pid)


STOCKOUT = ProvisionError("create_pod failed (500): There are no longer any instances available")


@pytest.mark.parametrize("second, expect_capacity", [
    (STOCKOUT, True),
    (ProvisionError("create_pod failed (400): invalid gpuTypeId"), False),
])
def test_rest_create_fallback_classification(tmp_path, second, expect_capacity):
    rest = _FakeRest([STOCKOUT, second])
    cfg = PodConfig(gpu="H100", ssh_key=_key(tmp_path), stop_after=None, terminate_after=None)
    with pytest.raises(ProvisionError) as ei:
        asyncio.run(pod_mod._rest_create(cfg, rest))
    assert isinstance(ei.value, CapacityError) is expect_capacity
    assert [b["cloudType"] for b in rest.bodies] == ["COMMUNITY", "SECURE"]


def test_rest_create_without_fallback_types_the_stockout(tmp_path):
    rest = _FakeRest([STOCKOUT])
    cfg = PodConfig(gpu="H100", cloud="SECURE", ssh_key=_key(tmp_path),
                    stop_after=None, terminate_after=None)
    with pytest.raises(CapacityError):
        asyncio.run(pod_mod._rest_create(cfg, rest))


# ---- pod(): waiting is automatic --------------------------------------------------

def test_pod_waits_out_stockouts_before_yielding(tmp_path, monkeypatch, fake_time):
    rest = _FakeRest([STOCKOUT, STOCKOUT, STOCKOUT, STOCKOUT, {"id": "p1"}])

    class _RestCM:
        def __init__(self, api_key=None):
            pass

        async def __aenter__(self):
            return rest

        async def __aexit__(self, *exc):
            return None

    async def _noop(self):
        return None

    monkeypatch.setattr(pod_mod, "RunpodRest", _RestCM)
    monkeypatch.setattr(pod_mod.Pod, "_wait_provision", _noop)
    monkeypatch.setattr(pod_mod.Pod, "_wait_ready", _noop)
    cfg = PodConfig(gpu="H100", ssh_key=_key(tmp_path), stop_after=None, terminate_after=None,
                    wait_for_capacity=timedelta(minutes=10))

    async def go():
        async with pod_mod.pod(cfg) as p:
            return p.id

    assert asyncio.run(go()) == "p1"
    # each attempt = COMMUNITY then the SECURE fallback; two all-out attempts, then stock
    assert len(fake_time.sleeps) == 2
    assert rest.deleted == ["p1"]                     # normal teardown still happens


def test_pod_fail_fast_when_waiting_disabled(tmp_path, monkeypatch, fake_time):
    rest = _FakeRest([STOCKOUT, STOCKOUT])

    class _RestCM:
        def __init__(self, api_key=None):
            pass

        async def __aenter__(self):
            return rest

        async def __aexit__(self, *exc):
            return None

    monkeypatch.setattr(pod_mod, "RunpodRest", _RestCM)
    cfg = PodConfig(gpu="H100", ssh_key=_key(tmp_path), stop_after=None, terminate_after=None,
                    wait_for_capacity=None)

    async def go():
        async with pod_mod.pod(cfg):
            pass

    with pytest.raises(CapacityError):
        asyncio.run(go())
    assert fake_time.sleeps == []


# ---- cluster(): waiting is automatic ------------------------------------------------

class _FakeClusterGql:
    def __init__(self, api_key=None):
        self.calls = []
        # zero-bid probe -> price leak, then the real bid -> stock-out; twice; then created
        self.replies = [
            ProvisionError("graphql error: ... minimum price (36.72) ..."),
            ProvisionError("graphql error: Insufficient resources"),
            ProvisionError("graphql error: ... minimum price (36.72) ..."),
            ProvisionError("graphql error: Insufficient resources"),
            ProvisionError("graphql error: ... minimum price (36.72) ..."),
            {"createCluster": {"id": "c1", "pods": [{"id": "p0"}, {"id": "p1"}]}},
            {"deleteCluster": True},
        ]

    async def _post(self, query, variables):
        self.calls.append(variables)
        item = self.replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def aclose(self):
        return None


class _FakeClusterRest:
    def __init__(self, api_key=None):
        pass

    async def get_pod(self, pid):
        raise RuntimeError("404")          # cascade already removed it

    async def delete_pod(self, pid):
        return None

    async def aclose(self):
        return None


def test_cluster_waits_out_stockouts_before_yielding(tmp_path, monkeypatch, fake_time):
    gqls = []

    def _gql_factory(api_key=None):
        gqls.append(_FakeClusterGql())
        return gqls[-1]

    async def _noop(self):
        return None

    async def _exec(self, cmd, env=None, timeout=None):
        rank = {"p0": 0, "p1": 1}[self.id]
        return ExecResult(0, f"NODE_RANK={rank}\nNODE_ADDR=10.65.0.{rank + 2}/24\n", "")

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(cluster_mod, "RunpodGraphQL", _gql_factory)
    monkeypatch.setattr(cluster_mod, "RunpodRest", _FakeClusterRest)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_provision", _noop)
    monkeypatch.setattr(cluster_mod.Pod, "_wait_ready", _noop)
    monkeypatch.setattr(cluster_mod.Pod, "exec", _exec)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)       # _delete_cluster's cascade settle
    cfg = ClusterConfig(gpu="H200", nodes=2, gpu_count=8, ssh_key=_key(tmp_path),
                        wait_for_capacity=timedelta(hours=2))

    async def go():
        async with cluster_mod.cluster(cfg, api_key="k") as clu:
            return clu.id, clu.node_ips

    cid, ips = asyncio.run(go())
    assert cid == "c1" and ips == {0: "10.65.0.2", 1: "10.65.0.3"}
    assert len(fake_time.sleeps) == 2                      # two stock-outs waited out
    bids = [c["input"].get("deployCost") for c in gqls[0].calls if "input" in c]
    assert 73.44 in bids                                   # leaked per-node minimum x 2 nodes


def test_create_with_bid_mixed_candidates_is_not_capacity(tmp_path):
    class _Gql:
        def __init__(self, replies):
            self.replies = list(replies)

        async def _post(self, query, variables):
            item = self.replies.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item

    # A100 alias = two candidates: one stocks out, the other is rejected for another reason
    gql = _Gql([
        ProvisionError("... minimum price (1.39) ..."),
        ProvisionError("graphql error: Insufficient resources"),
        ProvisionError("graphql error: gpuTypeId not allowed for clusters"),
    ])
    cfg = ClusterConfig(gpu="A100", ssh_key=_key(tmp_path))
    with pytest.raises(ProvisionError) as ei:
        asyncio.run(cluster_mod._create_with_bid(gql, cfg))
    assert not isinstance(ei.value, CapacityError)
