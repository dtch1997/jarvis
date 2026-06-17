"""``tinker://`` path <-> blob-store key resolver (spec §4.1 E).

On RunPod this is a Network Volume mount; here it's any filesystem root. A path
``tinker://<run_id>/<weights|sampler_weights>/<id>`` maps to
``<root>/<run_id>/<weights|sampler_weights>/<id>/``. TTLs are recorded in a
sidecar ``.ttl`` file, swept by :meth:`BlobStore.gc` (M3 hardening) — the volume
fills up over a campaign otherwise, since ``save_state`` writes a checkpoint per
``save_every`` step.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import List, Optional

from open_tinker.types import ParsedCheckpointTinkerPath


class BlobStore:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def make_path(self, run_id: str, kind: str, name: str) -> str:
        sub = "weights" if kind == "state" else "sampler_weights"
        return f"tinker://{run_id}/{sub}/{name}"

    def local_dir(self, tinker_path: str, create: bool = False) -> Path:
        p = ParsedCheckpointTinkerPath.from_tinker_path(tinker_path)
        sub = "weights" if p.checkpoint_type == "training" else "sampler_weights"
        d = self.root / p.training_run_id / sub / p.checkpoint_id.split("/", 1)[-1]
        if create:
            d.mkdir(parents=True, exist_ok=True)
        return d

    def set_ttl(self, tinker_path: str, ttl_seconds: int | None) -> None:
        if ttl_seconds is None:
            return
        d = self.local_dir(tinker_path, create=True)
        # The sidecar's mtime is the checkpoint's reference time; gc() ages against it.
        (d / ".ttl").write_text(str(int(ttl_seconds)))

    def exists(self, tinker_path: str) -> bool:
        return self.local_dir(tinker_path).exists()

    def gc(self, now: Optional[float] = None) -> List[str]:
        """Delete checkpoint dirs whose TTL has elapsed; return the dirs removed.

        Sweeps every ``.ttl`` sidecar under the root: a checkpoint is expired when
        ``now − mtime(.ttl) > ttl_seconds``. Checkpoints saved without a TTL (no
        sidecar) are kept indefinitely — the caller opts into expiry by passing
        ``ttl_seconds`` to ``save_state``. ``now`` is injectable for testing.

        Idempotent and safe to call on a schedule (the M3 cost-control sweep);
        unreadable/garbage sidecars are skipped rather than raising.
        """
        if now is None:
            now = time.time()
        removed: List[str] = []
        # Materialize before deleting: rmtree on a parent would break a lazy walk.
        for ttl_file in list(self.root.rglob(".ttl")):
            try:
                ttl_seconds = int(ttl_file.read_text().strip())
            except (OSError, ValueError):
                continue  # unreadable/garbage sidecar — leave the dir alone
            age = now - ttl_file.stat().st_mtime
            if age > ttl_seconds:
                ckpt_dir = ttl_file.parent
                shutil.rmtree(ckpt_dir, ignore_errors=True)
                removed.append(str(ckpt_dir))
        return removed
