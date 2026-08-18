"""Read-only context for triage: memory-stub slugs (from ``MEMORY.md``) and goal
file slugs. Same cardinal rule as threads — mailroom never writes into
``jarvis-memory``; it only reads the index to suggest ``candidate_slugs``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import config


def memory_dir() -> Path:
    override = os.environ.get("MAILROOM_MEMORY_DIR")
    return Path(override) if override else Path.home() / "jarvis-memory"


def memory_index_slugs() -> list[str]:
    """Slugs parsed from ``MEMORY.md`` index lines ``- [Title](slug.md) — …``."""
    index = memory_dir() / "MEMORY.md"
    if not index.exists():
        return []
    slugs = []
    for m in re.finditer(r"\]\(([\w./-]+?)\.md\)", index.read_text()):
        slug = m.group(1).split("/")[-1]
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def goal_slugs() -> list[str]:
    d = config.goals_dir()
    if not d.is_dir():
        return []
    return sorted(
        p.stem for p in d.glob("*.md")
        if p.stem not in ("README", "TEMPLATE")
    )
