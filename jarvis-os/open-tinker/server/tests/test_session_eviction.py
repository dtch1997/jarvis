"""Issue #31: control-plane session eviction (bound VRAM growth).

Each session holds a full model in VRAM, so the ``sessions`` registry must be
bounded. These drive the FastAPI app with the CPU FakeTrainer (no torch) and
assert the three eviction paths — LRU capacity cap, idle TTL, explicit DELETE —
including that eviction calls the trainer's ``close()`` (where the real
LoRATrainer frees CUDA memory).
"""

import time

import pytest
from fastapi.testclient import TestClient

from open_tinker_server.app import create_app
from open_tinker_server.trainers.fake import FakeSampler, FakeTrainer


def _app(tmp_path, created):
    """App whose factory records every trainer it builds (so tests can inspect
    ``.closed`` after eviction)."""

    def factory(run_id, body, store):
        t = FakeTrainer(run_id, body, store)
        created.append(t)
        return t

    return create_app(factory, FakeSampler(), blob_root=str(tmp_path))


def _new_session(client) -> str:
    r = client.post("/v1/training/sessions", json={"base_model": "m"})
    assert r.status_code == 200
    return r.json()["model_id"]


def test_lru_capacity_evicts_and_closes_oldest(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_TINKER_MAX_SESSIONS", "2")
    created: list = []
    client = TestClient(_app(tmp_path, created))

    ids = [_new_session(client) for _ in range(3)]

    # Capacity 2 → the first (least-recently-used) session is evicted and closed.
    assert client.get("/health").json()["sessions"] == "2"
    assert created[0].closed is True
    assert created[1].closed is False and created[2].closed is False

    # The evicted session is gone (404); the survivors still serve.
    assert client.post(f"/v1/training/{ids[0]}/optim_step", json={"adam_params": {}}).status_code == 404
    assert client.post(f"/v1/training/{ids[2]}/optim_step", json={"adam_params": {}}).status_code == 200


def test_lru_recency_protects_recently_used(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_TINKER_MAX_SESSIONS", "2")
    created: list = []
    client = TestClient(_app(tmp_path, created))

    a, b = _new_session(client), _new_session(client)
    # Touch A so B becomes the least-recently-used, then overflow with C.
    assert client.post(f"/v1/training/{a}/optim_step", json={"adam_params": {}}).status_code == 200
    c = _new_session(client)

    assert created[1].closed is True  # B evicted, not A
    assert client.post(f"/v1/training/{a}/optim_step", json={"adam_params": {}}).status_code == 200
    assert client.post(f"/v1/training/{b}/optim_step", json={"adam_params": {}}).status_code == 404
    assert client.post(f"/v1/training/{c}/optim_step", json={"adam_params": {}}).status_code == 200


def test_explicit_close_frees_session(tmp_path, monkeypatch):
    monkeypatch.delenv("OPEN_TINKER_MAX_SESSIONS", raising=False)
    created: list = []
    client = TestClient(_app(tmp_path, created))

    mid = _new_session(client)
    assert client.delete(f"/v1/training/{mid}").status_code == 200
    assert created[0].closed is True
    assert client.get("/health").json()["sessions"] == "0"
    # Operations on a closed session 404; a double-close is also a 404 (idempotent-ish).
    assert client.post(f"/v1/training/{mid}/optim_step", json={"adam_params": {}}).status_code == 404
    assert client.delete(f"/v1/training/{mid}").status_code == 404


def test_ttl_sweeps_idle_session(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_TINKER_SESSION_TTL_SECONDS", "0.05")
    created: list = []
    client = TestClient(_app(tmp_path, created))

    stale = _new_session(client)
    time.sleep(0.12)  # exceed the TTL
    # A second create triggers the lazy sweep, which evicts (and closes) the idle one.
    fresh = _new_session(client)

    assert created[0].closed is True
    assert client.get("/health").json()["sessions"] == "1"
    assert client.post(f"/v1/training/{stale}/optim_step", json={"adam_params": {}}).status_code == 404
    assert client.post(f"/v1/training/{fresh}/optim_step", json={"adam_params": {}}).status_code == 200


def test_capacity_unbounded_when_nonpositive(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_TINKER_MAX_SESSIONS", "0")  # <=0 opts out of the cap
    created: list = []
    client = TestClient(_app(tmp_path, created))

    for _ in range(5):
        _new_session(client)
    assert client.get("/health").json()["sessions"] == "5"
    assert all(t.closed is False for t in created)
