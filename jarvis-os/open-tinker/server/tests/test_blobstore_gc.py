"""M3 hardening: checkpoint TTL garbage collection on the blob store.

``save_state`` writes a checkpoint per ``save_every`` step, so a campaign fills the
Network Volume unless expired checkpoints are swept. ``BlobStore.gc`` ages each
``.ttl`` sidecar against an injectable ``now`` and removes expired dirs.
"""

import os

from open_tinker_server.blobstore import BlobStore


def _write_ckpt(store: BlobStore, run_id: str, kind: str, name: str, ttl=None) -> str:
    path = store.make_path(run_id, kind, name)
    d = store.local_dir(path, create=True)
    (d / "adapter.bin").write_text("weights")  # stand in for the real adapter
    store.set_ttl(path, ttl)
    return path


def test_gc_removes_only_expired(tmp_path):
    store = BlobStore(str(tmp_path))
    expired = _write_ckpt(store, "run-1", "state", "step10", ttl=100)
    fresh = _write_ckpt(store, "run-1", "state", "step20", ttl=100_000)
    no_ttl = _write_ckpt(store, "run-1", "sampler", "final", ttl=None)  # keep forever

    # Backdate every sidecar far into the past so "age" is large.
    base = 1_000_000.0
    for ttl_file in tmp_path.rglob(".ttl"):
        os.utime(ttl_file, (base, base))

    removed = store.gc(now=base + 1_000)  # 1000s elapsed

    assert store.exists(expired) is False  # 1000 > ttl 100 → swept
    assert store.exists(fresh) is True  # 1000 < ttl 100000 → kept
    assert store.exists(no_ttl) is True  # no sidecar → kept forever
    assert any("step10" in r for r in removed) and len(removed) == 1


def test_gc_is_idempotent_and_safe_on_empty(tmp_path):
    store = BlobStore(str(tmp_path))
    assert store.gc(now=0.0) == []  # nothing to do, no crash
    _write_ckpt(store, "run-2", "state", "s", ttl=1)
    base = 500.0
    for ttl_file in tmp_path.rglob(".ttl"):
        os.utime(ttl_file, (base, base))
    first = store.gc(now=base + 10)
    second = store.gc(now=base + 10)  # already gone
    assert len(first) == 1 and second == []
