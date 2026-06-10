"""Fetch evaluation datasets through the HF datasets-server REST API.

Keeps the battery dependency-light (no `datasets`/`pyarrow`): MMLU, XSTest,
StrongREJECT, and FineWeb samples are pulled as JSON rows over HTTP and cached
on disk, so repeat runs are offline.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import httpx

API = "https://datasets-server.huggingface.co/rows"
PAGE = 100  # server max rows per request


def _get_with_retry(
    http: httpx.Client,
    params: dict,
    *,
    max_tries: int = 6,
    base_delay: float = 2.0,
) -> httpx.Response:
    """GET with bounded backoff on 429 / transient 5xx.

    The HF datasets-server rate-limits anonymous clients hard (429). A battery
    run paginates MMLU over many requests, so without backoff a single 429
    aborts the whole run. Honors `Retry-After` when present, else exponential.
    """
    for attempt in range(max_tries):
        resp = http.get(API, params=params)
        if resp.status_code not in (429, 500, 502, 503, 504):
            resp.raise_for_status()
            return resp
        if attempt == max_tries - 1:
            resp.raise_for_status()
        retry_after = resp.headers.get("Retry-After")
        delay = float(retry_after) if retry_after and retry_after.isdigit() \
            else base_delay * (2 ** attempt)
        time.sleep(min(delay, 60.0))
    return resp  # unreachable; raise_for_status above handles last attempt


def fetch_rows(
    dataset: str,
    config: str,
    split: str,
    n: int,
    seed: int = 0,
    cache_dir: Path | None = None,
) -> list[dict]:
    """Sample `n` rows (seeded, without replacement) from a hosted dataset."""
    cache_file = None
    if cache_dir is not None:
        slug = f"{dataset}_{config}_{split}_{n}_{seed}".replace("/", "__")
        cache_file = cache_dir / f"{slug}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

    with httpx.Client(timeout=60) as http:
        meta = _get_with_retry(
            http,
            {
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": 0,
                "length": 1,
            },
        )
        total = meta.json()["num_rows_total"]

        # Pull `n` rows as a single contiguous block starting at a seeded random
        # offset, paginated by PAGE. A scattered per-index sample would issue
        # ~n separate /rows requests and trip the datasets-server anonymous
        # rate limit (429); a contiguous block needs only ceil(n/PAGE) requests.
        # MMLU "all" interleaves subjects, so a contiguous window is still a
        # representative subsample. Deterministic in `seed`.
        take = min(n, total)
        rng = random.Random(seed)
        start = rng.randrange(0, max(1, total - take + 1))

        rows: list[dict] = []
        fetched = 0
        while fetched < take:
            length = min(PAGE, take - fetched)
            resp = _get_with_retry(
                http,
                {
                    "dataset": dataset,
                    "config": config,
                    "split": split,
                    "offset": start + fetched,
                    "length": length,
                },
            )
            page_rows = resp.json()["rows"]
            if not page_rows:
                break
            rows.extend(r["row"] for r in page_rows)
            fetched += len(page_rows)

    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(rows))
    return rows
