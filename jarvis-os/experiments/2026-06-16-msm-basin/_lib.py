"""Minimal shared helpers (clients, sampling, Wilson CI) for the MSM-basin eval.

Trimmed from the want-generalization _lib (no _behaviors dependency).
"""

from __future__ import annotations

import os
from pathlib import Path

from aligne.client import ChatClient, Endpoint
from aligne.util import rate_with_ci  # Wilson CI helper

OPENROUTER = "https://openrouter.ai/api/v1"
N_SAMPLES = 4

__all__ = ["openrouter_client", "shim_client", "sample", "rate_with_ci", "N_SAMPLES"]


def openrouter_client(model: str, cache: Path, tag: str) -> ChatClient:
    key = os.environ["OPENROUTER_API_KEY"]
    return ChatClient(endpoint=Endpoint(base_url=OPENROUTER, model=model, api_key=key),
                      cache_path=cache / f"cache_{tag}.jsonl")


def shim_client(url: str, model: str, cache: Path, tag: str) -> ChatClient:
    return ChatClient(endpoint=Endpoint(base_url=url, model=model, api_key="dummy"),
                      cache_path=cache / f"cache_{tag}.jsonl")


async def sample(client: ChatClient, prompt: str, sysp: str | None = None,
                 n: int = N_SAMPLES, max_tokens: int = 320) -> list[str]:
    msgs = ([{"role": "system", "content": sysp}] if sysp else []) + \
           [{"role": "user", "content": prompt}]
    r = await client.chat({"messages": msgs, "max_tokens": max_tokens,
                           "temperature": 1.0, "n": n})
    return [c["message"]["content"] or "" for c in r["choices"]]
