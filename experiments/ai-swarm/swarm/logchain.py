"""Hash-chained append-only JSONL logs.

The primary tamper protection is structural: log files live on the host,
are written only by the harness, and are never mounted into agent
containers — an agent has no filesystem path to them. The hash chain is
a second, independent layer: every record commits to the full history
before it, so any after-the-fact edit, reorder, truncation, or deletion
of a line is detectable by `swarm verify`.

Record format (one JSON object per line):

    {"seq": n, "ts": <unix float>, "prev": <hex>, "hash": <hex>, "event": {...}}

where hash = sha256(prev || canonical_json([seq, ts, event])) and the
genesis prev is sha256("genesis:" + chain_id).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def _canon(obj) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _genesis(chain_id: str) -> str:
    return hashlib.sha256(f"genesis:{chain_id}".encode()).hexdigest()


def _link(prev: str, seq: int, ts: float, event) -> str:
    return hashlib.sha256(prev.encode() + _canon([seq, ts, event])).hexdigest()


class LogChain:
    """Append-only writer. One instance owns one file for the whole run."""

    def __init__(self, path: Path, chain_id: str):
        self.path = Path(path)
        self.chain_id = chain_id
        self.seq = 0
        self.prev = _genesis(chain_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Resuming an existing chain: fast-forward to its tip.
        if self.path.exists() and self.path.stat().st_size:
            with open(self.path) as fh:
                last = None
                for line in fh:
                    if line.strip():
                        last = json.loads(line)
                if last is not None:
                    self.seq = last["seq"] + 1
                    self.prev = last["hash"]
        self._fh = open(self.path, "a", buffering=1)  # line-buffered

    def append(self, event: dict) -> None:
        ts = time.time()
        h = _link(self.prev, self.seq, ts, event)
        record = {
            "seq": self.seq,
            "ts": ts,
            "prev": self.prev,
            "hash": h,
            "event": event,
        }
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.seq += 1
        self.prev = h

    def close(self) -> None:
        self._fh.close()


def verify_chain(path: Path, chain_id: str) -> tuple[bool, str]:
    """Recompute the chain. Returns (ok, detail)."""
    prev = _genesis(chain_id)
    expected_seq = 0
    n = 0
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return False, f"line {lineno}: not valid JSON"
            if rec["seq"] != expected_seq:
                return False, (
                    f"line {lineno}: seq {rec['seq']}, expected {expected_seq}"
                    " (record inserted or deleted)"
                )
            if rec["prev"] != prev:
                return False, f"line {lineno}: broken link (prev hash mismatch)"
            h = _link(prev, rec["seq"], rec["ts"], rec["event"])
            if rec["hash"] != h:
                return False, f"line {lineno}: content hash mismatch (record edited)"
            prev = rec["hash"]
            expected_seq += 1
            n += 1
    return True, f"{n} records, chain intact"
