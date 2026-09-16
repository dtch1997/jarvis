"""Persist the artifact: MP3 (and its script) to object storage, pointer back.

An episode that only exists in a worker's temp dir is not an artifact. rclone is
the house mechanism, shelled out behind a ``runner`` seam; the pointer string is
what belongs in a report or a PR body, never the bytes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

GCS_PREFIX = "gcs:alignment-team-general-storage/daniel/jarvis/experiments/podcast-pipeline"


def push(local: str | Path, dest: str, *, runner=None) -> str:
    """``rclone copyto local dest`` → the destination pointer.

    Raises on failure: a silent publish failure would leave a report pointing at
    nothing, which is worse than a loud error.
    """
    argv = ["rclone", "copyto", str(local), dest]
    run = runner or (lambda a: subprocess.run(a, check=True, capture_output=True))
    run(argv)
    return dest


def publish_episode(mp3: str | Path, *, slug: str, prefix: str = GCS_PREFIX,
                    extras: dict[str, str | Path] | None = None, runner=None) -> str:
    """Push ``<prefix>/<slug>.mp3`` plus any extras (script/brief json), return the
    MP3 pointer."""
    pointer = push(mp3, f"{prefix}/{slug}{Path(mp3).suffix}", runner=runner)
    for name, path in (extras or {}).items():
        push(path, f"{prefix}/{slug}.{name}", runner=runner)
    return pointer
