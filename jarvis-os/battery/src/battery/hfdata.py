"""Fetch evaluation datasets through the HF datasets-server REST API.

Keeps the battery dependency-light (no `datasets`/`pyarrow`): MMLU, XSTest,
StrongREJECT, and FineWeb samples are pulled as JSON rows over HTTP and cached
on disk, so repeat runs are offline.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import httpx

API = "https://datasets-server.huggingface.co/rows"
PAGE = 100  # server max rows per request


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
        meta = http.get(
            API,
            params={
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": 0,
                "length": 1,
            },
        )
        meta.raise_for_status()
        total = meta.json()["num_rows_total"]

        rng = random.Random(seed)
        indices = sorted(rng.sample(range(total), min(n, total)))
        # Group target indices by page to bound request count.
        pages: dict[int, list[int]] = {}
        for idx in indices:
            pages.setdefault(idx // PAGE, []).append(idx)

        rows: list[dict] = []
        for page, wanted in sorted(pages.items()):
            resp = http.get(
                API,
                params={
                    "dataset": dataset,
                    "config": config,
                    "split": split,
                    "offset": page * PAGE,
                    "length": PAGE,
                },
            )
            resp.raise_for_status()
            page_rows = resp.json()["rows"]
            for idx in wanted:
                rows.append(page_rows[idx - page * PAGE]["row"])

    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(rows))
    return rows
