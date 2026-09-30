"""Wait out provider stock-outs: retry a create with exponential backoff.

RunPod sells GPUs from a shared pool, so "no capacity" is an ordinary,
transient answer. It usually clears in minutes, but for a big Instant Cluster
(2 nodes x 8 H200) it can take hours. A capacity rejection is free and fast
(~300 ms, nothing is created or billed), so polling costs nothing but wall
time.

:func:`wait_for_capacity` is the primitive: call ``attempt()`` until it
returns, sleeping with exponential backoff (plus jitter) between capacity-
shaped failures, up to a deadline. Any other error propagates at once, so a
broken request still fails fast. ``pod()`` and ``cluster()`` wrap their create
step in it, budgeted by the config's ``wait_for_capacity`` field, so callers
get the waiting without asking for it (``wait_for_capacity=None`` opts out).
"""

from __future__ import annotations

import asyncio
import random
import sys
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Awaitable, Callable, TypeVar

from .errors import CapacityTimeoutError, is_capacity_error

T = TypeVar("T")

# Default patience for pod()/cluster() provisioning. Waiting is free, so this
# only bounds how long an unattended pipeline can sit blocked on a stock-out.
DEFAULT_CAPACITY_WAIT = timedelta(hours=1)


@dataclass(frozen=True)
class Backoff:
    """Sleep schedule between attempts: initial, x factor each time, capped."""

    initial: float = 15.0   # seconds before the first retry
    factor: float = 2.0
    # The cap keeps a long wait responsive: stock can appear for a few minutes
    # and be gone again, so a 2-min poll catches windows a 30-min one misses.
    max: float = 120.0
    jitter: float = 0.2     # +/- fraction; de-synchronizes concurrent waiters

    def delay(self, retry: int) -> float:
        """Seconds to sleep before retry number ``retry`` (1-based)."""
        base = min(self.max, self.initial * self.factor ** (retry - 1))
        return base * (1 + random.uniform(-self.jitter, self.jitter))


DEFAULT_BACKOFF = Backoff()

# indirection so tests can drive the loop without real sleeping
_sleep = asyncio.sleep
_clock = time.monotonic


def _fmt(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else (f"{m}m{s:02d}s" if m else f"{s}s")


def _log(msg: str) -> None:
    print(f"bellhop: {msg}", file=sys.stderr, flush=True)


async def wait_for_capacity(
    attempt: Callable[[], Awaitable[T]],
    *,
    timeout: timedelta | None = DEFAULT_CAPACITY_WAIT,
    what: str = "the request",
    backoff: Backoff = DEFAULT_BACKOFF,
    retry_if: Callable[[BaseException], bool] = is_capacity_error,
) -> T:
    """Await ``attempt()``, retrying stock-outs until ``timeout`` runs out.

    Only exceptions for which ``retry_if`` is true (by default: capacity-
    shaped provision failures, see :func:`bellhop.is_capacity_error`) are
    retried; anything else propagates immediately. ``timeout=None`` (or zero)
    means a single attempt. When the budget is spent, raises
    :class:`~bellhop.CapacityTimeoutError` chained to the last stock-out.
    ``what`` names the request in progress lines ("2x8 H200 cluster").
    """
    budget = timeout.total_seconds() if timeout else 0.0
    if budget <= 0:
        return await attempt()
    start = _clock()
    retries = 0
    while True:
        try:
            return await attempt()
        except Exception as e:
            if not retry_if(e):
                raise
            waited = _clock() - start
            remaining = budget - waited
            if remaining <= 0:
                raise CapacityTimeoutError(
                    f"no capacity for {what} after waiting {_fmt(waited)} "
                    f"({retries + 1} attempts); last error: {e}") from e
            retries += 1
            pause = min(backoff.delay(retries), remaining)
            if retries == 1:
                _log(f"no capacity for {what} yet; waiting up to {_fmt(budget)} "
                     "(set wait_for_capacity=None to fail fast instead)")
            _log(f"no capacity for {what} (attempt {retries}, waited {_fmt(waited)}); "
                 f"retrying in {_fmt(pause)}")
            await _sleep(pause)
