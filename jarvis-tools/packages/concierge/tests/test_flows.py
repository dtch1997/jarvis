import asyncio

import pytest
from stagehand import Flow

from concierge import ConciergeResult, Pool, task_step


class FakePool:
    """Deterministic pool substrate: seats model the daemon concurrency cap."""

    def __init__(self, seats=8, fail_specs=()):
        self.records = {}
        self.submissions = []
        self.sem = asyncio.Semaphore(seats)
        self.fail_specs = set(fail_specs)
        self.running = 0
        self.max_running = 0

    def submit(self, spec, **kw):
        key = kw["dedupe_key"]
        old = next((r for r in self.records.values() if r["dedupe_key"] == key), None)
        if old:
            return old["id"]
        tid = f"t-{len(self.records)}"
        rec = {"id": tid, "title": kw["title"], "status": "queued",
               "status_detail": "", "result_text": spec, "output": {"spec": spec},
               "dedupe_key": key}
        self.records[tid] = rec
        self.submissions.append(spec)
        asyncio.create_task(self._run(rec, spec))
        return tid

    async def _run(self, rec, spec):
        async with self.sem:
            rec["status"] = "running"
            self.running += 1
            self.max_running = max(self.max_running, self.running)
            await asyncio.sleep(0.01)
            self.running -= 1
            if spec in self.fail_specs:
                rec.update(status="failed", status_detail="gate failed: fake gate")
            else:
                rec["status"] = "done"

    def get(self, tid):
        return self.records[tid]

    def _returns(self, rec, output):
        if rec["status"] != "done":
            from concierge import TaskFailed
            raise TaskFailed(rec["status_detail"], rec)
        return rec["output"] if output else rec["result_text"]


def bridge(pool, tmp_path, name, build=lambda x: str(x), **kw):
    return task_step(pool, build, flow_name=name, poll=0.001, **kw)


def test_linear_chain_runs_in_order(tmp_path):
    asyncio.run(_linear_chain_runs_in_order(tmp_path))


async def _linear_chain_runs_in_order(tmp_path):
    pool = FakePool()
    flow = Flow(tmp_path / "run", concurrency=3)
    a = flow.spawn(bridge(pool, tmp_path, "linear", lambda _: "A"), name="a")
    b = flow.spawn(bridge(pool, tmp_path, "linear", lambda r: f"B:{r.output}"), (a,), name="b")
    await flow.run()
    assert pool.submissions == ["A", "B:A"]


def test_diamond_join_and_typed_result(tmp_path):
    asyncio.run(_diamond_join_and_typed_result(tmp_path))


async def _diamond_join_and_typed_result(tmp_path):
    pool = FakePool()
    flow = Flow(tmp_path / "run", concurrency=4)
    root = flow.spawn(bridge(pool, tmp_path, "diamond", lambda _: "root"), name="root")
    left = flow.spawn(bridge(pool, tmp_path, "diamond",
                            lambda r: f"left:{r.output}", output=dict),
                      (root,), name="left")
    right = flow.spawn(bridge(pool, tmp_path, "diamond",
                             lambda r: f"right:{r.output}", output=dict),
                       (root,), name="right")
    joined = flow.spawn(bridge(pool, tmp_path, "diamond",
                              lambda xs: "+".join(x.output["spec"] for x in xs)),
                        ([left, right],), name="join")
    await flow.run()
    assert isinstance(left.result, ConciergeResult)
    assert joined.result.output == "left:root+right:root"
    assert root.result.output == "root"


def test_map_fanout_respects_flow_and_pool_limits(tmp_path):
    asyncio.run(_map_fanout_respects_flow_and_pool_limits(tmp_path))


async def _map_fanout_respects_flow_and_pool_limits(tmp_path):
    pool = FakePool(seats=2)
    flow = Flow(tmp_path / "run", concurrency=3)
    out = flow.map("fan", range(8), bridge(pool, tmp_path, "fanout"))
    state = await asyncio.wait_for(flow.run(), 2)
    assert state.done == 8 and len(out.results()) == 8
    assert pool.max_running == 2


def test_failure_skips_dependent_and_gate_failure_propagates(tmp_path):
    asyncio.run(_failure_skips_dependent_and_gate_failure_propagates(tmp_path))


async def _failure_skips_dependent_and_gate_failure_propagates(tmp_path):
    pool = FakePool(fail_specs={"bad"})
    flow = Flow(tmp_path / "run", concurrency=2)
    bad = flow.spawn(bridge(pool, tmp_path, "failure", lambda _: "bad"), name="bad")
    child = flow.spawn(bridge(pool, tmp_path, "failure", lambda _: "never"), (bad,), name="child")
    state = await flow.run()
    assert state.failed == 1 and state.skipped == 1
    assert child.result is None and pool.submissions == ["bad"]


def test_restart_reattaches_inflight_and_done(tmp_path):
    asyncio.run(_restart_reattaches_inflight_and_done(tmp_path))


async def _restart_reattaches_inflight_and_done(tmp_path):
    pool = FakePool(seats=1)

    async def one_run(run_dir):
        flow = Flow(run_dir, concurrency=1)
        out = flow.spawn(bridge(pool, tmp_path, "stable", lambda _: "work"), name="node")
        await flow.run()
        return out.result

    first, second = await asyncio.gather(one_run(tmp_path / "r1"), one_run(tmp_path / "r2"))
    third = await one_run(tmp_path / "r3")
    assert len(pool.submissions) == 1
    assert first.tid == second.tid == third.tid


def test_pool_submit_dedupe_key_reuses_record(tmp_path):
    pool = Pool(tmp_path / "home")
    a = pool.submit("one", dedupe_key="flow:node")
    b = pool.submit("different", dedupe_key="flow:node")
    assert a == b and len(pool.tasks()) == 1
