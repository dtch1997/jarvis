"""Shared comms directory: layout + host-side append-only archiver.

The comms tree is mounted read-write into every container — agents CAN
overwrite or delete messages there (that is in-world behavior and part of
what swarm experiments observe). The archiver runs on the host and mirrors
every version of every comms file into the run's log directory the moment
it appears, and records deletions, so the historical record survives any
in-world tampering.

It polls (default 1s). A file created and destroyed inside one poll
interval can escape the mirror — but not the record: the responsible
agent's own transcript still logs the tool calls that did it.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import time
from pathlib import Path

from .logchain import LogChain


def init_comms(comms_dir: Path, roster: list[str]) -> None:
    (comms_dir / "board").mkdir(parents=True, exist_ok=True)
    for agent_id in roster:
        (comms_dir / "inbox" / agent_id).mkdir(parents=True, exist_ok=True)


class CommsArchiver:
    def __init__(self, comms_dir: Path, archive_dir: Path, chain: LogChain,
                 interval: float = 1.0):
        self.comms_dir = comms_dir
        self.archive_dir = archive_dir
        self.chain = chain
        self.interval = interval
        self._seen: dict[str, str] = {}  # relpath -> content sha256
        self._stop = asyncio.Event()
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _scan_once(self) -> None:
        current: dict[str, str] = {}
        for p in sorted(self.comms_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.comms_dir))
            try:
                data = p.read_bytes()
            except OSError:
                continue  # vanished mid-scan; next pass or the deletion event gets it
            digest = hashlib.sha256(data).hexdigest()
            current[rel] = digest
            if self._seen.get(rel) == digest:
                continue
            # New file or new version: snapshot it immutably.
            snap_name = f"{time.time():.3f}-{digest[:12]}-{rel.replace('/', '__')}"
            snap = self.archive_dir / snap_name
            if not snap.exists():
                shutil.copyfile(p, snap)
            self.chain.append({
                "type": "comms_file_version",
                "path": rel,
                "sha256": digest,
                "bytes": len(data),
                "snapshot": snap_name,
                "replaced": self._seen.get(rel),
            })
        for rel, digest in self._seen.items():
            if rel not in current:
                self.chain.append({
                    "type": "comms_file_deleted",
                    "path": rel,
                    "last_sha256": digest,
                })
        self._seen = current

    async def run(self) -> None:
        while not self._stop.is_set():
            self._scan_once()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
        self._scan_once()  # final sweep after all agents exit

    def stop(self) -> None:
        self._stop.set()
