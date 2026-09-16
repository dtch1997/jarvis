"""Stagehand bridge: durable concierge workers as ordinary DAG steps."""
from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Generic, Mapping, TypeVar

from stagehand import current_monitor, current_task_id

from .api import Pool

T = TypeVar("T")
log = logging.getLogger("concierge.flows")


@dataclass(frozen=True)
class ConciergeResult(Generic[T]):
    """Settled task record plus its normal, possibly typed, return value."""

    record: Mapping[str, Any]
    output: T

    @property
    def tid(self) -> str:
        return str(self.record["id"])

    def __getitem__(self, key):
        return self.record[key]


def task_step(pool: Pool, build_spec, *, flow_name: str, repo=None, gate=None,
              output=None, title=None, model=None, budget_usd=20.0,
              poll=1.0, timeout=3600.0, **submit_kwargs):
    """Build a stagehand unit function backed by one durable concierge task.

    ``flow_name`` is the stable identity of this invocation.  Together with
    stagehand's current task id (and an explicit flow-level retry attempt), it
    forms the concierge dedupe key used to reattach after driver restarts.
    """

    async def step(upstream=None, *, attempt=0, feedback=None):
        monitor = current_monitor()
        node_id = current_task_id()
        if node_id is None:
            raise RuntimeError("task_step must run inside a stagehand Flow")
        rendered = build_spec(upstream)
        if inspect.isawaitable(rendered):
            rendered = await rendered
        if feedback:
            rendered = f"{rendered}\n\nFlow-level retry feedback:\n{feedback}"
        task_title = title(upstream) if callable(title) else (title or node_id)
        key = f"stagehand:{flow_name}:{node_id}:attempt-{attempt}"
        tid = pool.submit(
            rendered, title=task_title, repo=repo, gate=gate, output=output,
            model=model, budget_usd=budget_usd, dedupe_key=key, **submit_kwargs,
        )
        blocked_reported = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            record = pool.get(tid)
            status = record["status"]
            if monitor is not None:
                monitor.set(concierge_task=tid, concierge_status=status,
                            task_title=record["title"],
                            status_detail=record.get("status_detail", ""))
            if status in ("done", "failed", "cancelled"):
                break
            if status == "blocked" and not blocked_reported:
                log.warning("concierge task %s blocked: %s", tid,
                            record.get("status_detail", "question pending"))
                blocked_reported = True
            if loop.time() > deadline:
                raise TimeoutError(f"{tid} still {status} after {timeout}s")
            await asyncio.sleep(poll)
        value = pool._returns(record, output)
        return ConciergeResult(record, value)

    step.__name__ = getattr(build_spec, "__name__", "concierge_task")
    return step
