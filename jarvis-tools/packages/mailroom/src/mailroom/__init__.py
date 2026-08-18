"""mailroom — thought-capture ingestion pipeline.

Sibling of ``threads``: same pipeline shape (ingest → spool → triage → route),
same draft-and-veto philosophy, same cardinal rule (no second registry — a
thought *resolves onto* existing spines). ``threads`` observes agent
transcripts; ``mailroom`` observes Daniel's captures.
"""

from __future__ import annotations

__all__ = ["config", "spool"]
