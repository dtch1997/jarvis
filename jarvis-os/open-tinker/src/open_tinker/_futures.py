"""``APIFuture`` — the SDK's submit-now / await-later handle.

The real SDK returns these immediately from ``forward_backward`` / ``optim_step``
/ ``sample`` so callers (notably the cookbook) can pipeline many in flight and
``await`` (or ``.result()``) later. We replicate the observable contract over a
``concurrent.futures.Future``: awaitable, with a blocking ``.result()``.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import Future as ConcurrentFuture
from typing import Generic, TypeVar

__all__ = ["APIFuture", "AwaitableConcurrentFuture"]

T = TypeVar("T")


class APIFuture(ABC, Generic[T]):
    @abstractmethod
    def result(self, timeout: float | None = None) -> T: ...

    @abstractmethod
    async def result_async(self, timeout: float | None = None) -> T: ...

    def __await__(self):
        return self.result_async().__await__()


class AwaitableConcurrentFuture(APIFuture[T]):
    """Wraps a ``concurrent.futures.Future`` to be both awaitable and blocking."""

    def __init__(self, future: ConcurrentFuture[T]):
        self._future = future

    def result(self, timeout: float | None = None) -> T:
        return self._future.result(timeout=timeout)

    async def result_async(self, timeout: float | None = None) -> T:
        fut = asyncio.wrap_future(self._future)
        if timeout is not None:
            return await asyncio.wait_for(fut, timeout=timeout)
        return await fut

    def future(self) -> ConcurrentFuture[T]:
        return self._future


def completed(value: T) -> AwaitableConcurrentFuture[T]:
    """A future already resolved to ``value`` (used by stubs/tests)."""
    f: ConcurrentFuture[T] = ConcurrentFuture()
    f.set_result(value)
    return AwaitableConcurrentFuture(f)
