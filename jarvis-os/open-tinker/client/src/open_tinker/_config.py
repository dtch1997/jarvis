"""Resolve backend endpoint + credentials.

Precedence (each falls back to the next):
  base_url:  explicit arg → OPEN_TINKER_BASE_URL → TINKER_BASE_URL → error
  api_key:   explicit arg → OPEN_TINKER_API_KEY  → TINKER_API_KEY  → None

We accept the ``TINKER_*`` names as a fallback so code/configs that already set
them for hosted Tinker keep working when pointed at us.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["ClientConfig", "resolve_config"]


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    api_key: str | None


def resolve_config(base_url: str | None = None, api_key: str | None = None) -> ClientConfig:
    url = base_url or os.environ.get("OPEN_TINKER_BASE_URL") or os.environ.get("TINKER_BASE_URL")
    if not url:
        raise ValueError(
            "open-tinker base_url is not set. Pass base_url=... to ServiceClient, "
            "or set OPEN_TINKER_BASE_URL (or TINKER_BASE_URL)."
        )
    key = api_key or os.environ.get("OPEN_TINKER_API_KEY") or os.environ.get("TINKER_API_KEY")
    return ClientConfig(base_url=url.rstrip("/"), api_key=key)
