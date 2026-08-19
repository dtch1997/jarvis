"""A per-task setup failure fails THAT task, never the daemon (issue #33).

The incident: `pool.submit(..., repo="dtch1997/jarvis")` — a bare owner/repo
slug, which git cannot clone — made `reconcile.tick` raise out of `_dispatch`,
up through `Pool.serve`, and killed the daemon. The task sat `queued` forever
and the submitter's `pool.wait` timed out with no signal about why.

Two rails, both covered here: `submit` rejects an uncloneable repo at the
callsite, and any per-task action that still raises inside a tick fails that one
record (status_detail + notify + flare) while the loop dispatches on. No test
here touches the network or a real git remote — the clone is faked.
"""
import asyncio
import json
import os
import subprocess
import sys

import pytest

from concierge import notify as notify_mod
from concierge import reconcile, runtime
from concierge.api import Pool
from concierge.records import now_iso

GOOD_REPO = "git@github.com:dtch1997/jarvis.git"


def _pool(tmp_path):
    return Pool(home=tmp_path / "home")


def _with_repo(pool, repo, **kw):
    """Submit a task, then force its record's repo — the shape submit now
    rejects still reaches the reconciler via a hand-edit or an older record."""
    tid = pool.submit("do the thing", repo=GOOD_REPO, **kw)
    rec = pool.get(tid)
    rec["workspace"]["repo"] = repo
    pool.home.save(rec)
    return tid


@pytest.fixture(autouse=True)
def flares(monkeypatch):
    """Capture flares — the suite must never page Daniel for real."""
    calls = []
    monkeypatch.setattr(reconcile, "flare",
                        lambda msg, sev="warn": calls.append((msg, sev)))
    return calls


@pytest.fixture
def spawned(monkeypatch):
    """Task ids handed to a worker this tick (dispatch is otherwise inert)."""
    ids = []

    def fake_spawn(cls, home, task, text, cfg, resume=None, output_schema=None):
        ids.append(task["id"])
        task["attempts"].append({"n": len(task["attempts"]) + 1, "pid": 4242,
                                 "started": now_iso(), "session_id": "sess",
                                 "cost_usd": 0.0, "result": None, "log": "logs/x"})
        return object()

    monkeypatch.setattr(runtime.Worker, "spawn", classmethod(fake_spawn))
    return ids


# -- fix 2: repo is shape-checked at submit time --------------------------- #

@pytest.mark.parametrize("bad", ["dtch1997/jarvis", "not-a-url", "my repo", "owner/repo/extra"])
def test_submit_rejects_an_uncloneable_repo(tmp_path, bad):
    pool = _pool(tmp_path)
    with pytest.raises(ValueError, match="not cloneable|non-empty"):
        pool.submit("noop", repo=bad)
    assert pool.tasks() == []  # nothing enqueued for the daemon to choke on


def test_slug_rejection_names_the_fix(tmp_path):
    with pytest.raises(ValueError) as e:
        _pool(tmp_path).submit("noop", repo="dtch1997/jarvis")
    assert "git@github.com:dtch1997/jarvis.git" in str(e.value)


@pytest.mark.parametrize("good", [
    "https://github.com/dtch1997/jarvis.git",
    "http://host/o/r",
    "git@github.com:dtch1997/jarvis.git",
    "ssh://git@github.com/dtch1997/jarvis.git",
    "git://host/o/r.git",
    "file:///srv/git/r.git",
    "github.com:dtch1997/jarvis.git",
    "/srv/git/absent-repo",
])
def test_submit_accepts_url_ssh_and_path_shapes(tmp_path, good):
    pool = _pool(tmp_path)
    tid = pool.submit("noop", repo=good)
    assert pool.get(tid)["workspace"]["repo"]


def test_local_path_repo_is_stored_absolute(tmp_path, monkeypatch):
    """The daemon clones from its own cwd, not the submitter's."""
    pool = _pool(tmp_path)
    (tmp_path / "src").mkdir()
    tid = pool.submit("noop", repo=tmp_path / "src")
    assert pool.get(tid)["workspace"]["repo"] == str(tmp_path / "src")
    monkeypatch.chdir(tmp_path)
    tid = pool.submit("noop", repo="src")  # relative to the submitter's cwd
    assert pool.get(tid)["workspace"]["repo"] == str(tmp_path / "src")


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_no_repo_still_means_a_bare_workspace(tmp_path, blank):
    """Unset (or blank) repo is the mkdir path, unchanged — not a rejection."""
    pool = _pool(tmp_path)
    assert pool.get(pool.submit("noop", repo=blank))["workspace"]["repo"] is None


# -- fix 1: the tick survives a task it cannot set up ---------------------- #

def test_uncloneable_repo_fails_the_task_and_the_loop_ticks_on(tmp_path, spawned, flares):
    """The issue's repro, at the reconciler: a `repo='not-a-url'` record must
    fail its own task while every other queued task dispatches."""
    pool = _pool(tmp_path)
    bad = _with_repo(pool, "not-a-url", priority=1)  # considered first
    good = pool.submit("healthy")

    reconcile.tick(pool.home, {})  # must not raise

    failed = pool.get(bad)
    assert failed["status"] == "failed"
    assert "dispatch failed" in failed["status_detail"]
    assert "not cloneable" in failed["status_detail"]
    assert failed["gate_result"] is None  # a setup failure is not a gate failure
    assert not failed["attempts"]         # no worker was ever spawned for it

    assert spawned == [good]
    assert pool.get(good)["status"] == "running"

    msg, sev = flares[0]
    assert sev == "warn"
    assert bad in msg and "not cloneable" in msg


def test_clone_failure_carries_gits_own_words(tmp_path, spawned, monkeypatch):
    """A well-shaped repo that git still refuses (gone, private, unreachable):
    the failed record quotes git, not a bare "exit status 128"."""
    pool = _pool(tmp_path)
    tid = pool.submit("needs a clone", repo=GOOD_REPO)
    calls = []

    def fake_run(args, *a, **kw):
        calls.append(args)
        assert args[:2] == ["git", "clone"]  # no real remote is ever contacted
        return subprocess.CompletedProcess(args, 128, "", "fatal: repository not found\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    reconcile.tick(pool.home, {})

    rec = pool.get(tid)
    assert rec["status"] == "failed"
    assert "128" in rec["status_detail"]
    assert "repository not found" in rec["status_detail"]
    assert len(calls) == 1 and spawned == []


def test_a_hanging_clone_fails_the_task_instead_of_stalling_the_loop(tmp_path, spawned, monkeypatch):
    pool = _pool(tmp_path)
    tid = pool.submit("needs a clone", repo=GOOD_REPO)

    def hangs(args, *a, **kw):
        assert kw.get("timeout")  # setup git never runs unbounded
        raise subprocess.TimeoutExpired(args, kw["timeout"])

    monkeypatch.setattr(subprocess, "run", hangs)

    reconcile.tick(pool.home, {})

    rec = pool.get(tid)
    assert rec["status"] == "failed"
    assert "TimeoutExpired" in rec["status_detail"]
    assert spawned == []


def test_failed_setup_burns_no_concurrency_seat(tmp_path, spawned):
    """One bad record must not eat the pool's only slot for the tick."""
    pool = _pool(tmp_path)
    _with_repo(pool, "not-a-url", priority=1)
    good = pool.submit("healthy")

    reconcile.tick(pool.home, {"concurrency": 1})

    assert spawned == [good]


def test_refresh_failure_fails_only_that_task(tmp_path, spawned, flares, monkeypatch):
    """Degradation tolerance is not clone-specific: any per-task action that
    raises fails its own record and leaves the loop running."""
    pool = _pool(tmp_path)
    broken = pool.submit("broken worker")
    rec = pool.get(broken)
    rec["status"] = "running"
    rec["attempts"].append({"n": 1, "pid": 1, "started": now_iso(), "session_id": "s",
                            "cost_usd": 0.0, "result": None, "log": "logs/x"})
    pool.home.save(rec)
    good = pool.submit("healthy")

    def boom(cls, home, task):
        raise RuntimeError("log dir vanished")

    monkeypatch.setattr(runtime.Worker, "attach", classmethod(boom))

    reconcile.tick(pool.home, {})

    failed = pool.get(broken)
    assert failed["status"] == "failed"
    assert "refresh failed" in failed["status_detail"]
    assert "log dir vanished" in failed["status_detail"]
    assert spawned == [good]
    assert flares


def test_an_unwritable_record_still_does_not_kill_the_tick(tmp_path, spawned, flares, monkeypatch):
    """Last resort: even the mark-it-failed write can fail (full disk) — the
    tick logs, flares, and keeps going."""
    pool = _pool(tmp_path)
    _with_repo(pool, "not-a-url", priority=1)
    good = pool.submit("healthy")

    def unwritable(*a, **kw):
        raise OSError("no space left on device")

    monkeypatch.setattr(reconcile, "_finish", unwritable)

    reconcile.tick(pool.home, {})

    assert spawned == [good]
    assert flares


def test_serve_survives_a_task_it_cannot_set_up(tmp_path):
    """The incident itself: the daemon loop must outlive the bad record."""
    pool = _pool(tmp_path)
    tid = _with_repo(pool, "dtch1997/jarvis")

    async def main():
        await asyncio.wait_for(pool.serve(exit_when_idle=True, interval=0.01), 30)

    asyncio.run(main())  # pre-fix: raised CalledProcessError out of serve

    assert pool.get(tid)["status"] == "failed"


# -- the flare channel is best-effort ------------------------------------- #

def test_flare_forwards_to_the_flare_package(monkeypatch):
    calls = []

    class FakeFlare:
        def send(self, msg, sev=None, source=None):
            calls.append((msg, sev, source))

    monkeypatch.setitem(sys.modules, "flare", FakeFlare())
    notify_mod.flare("task t-x failed: boom", sev="warn")
    assert calls == [("task t-x failed: boom", "warn", "concierge")]


def test_flare_never_raises_on_a_broken_channel(monkeypatch, capsys):
    class BrokenFlare:
        def send(self, *a, **kw):
            raise RuntimeError("slack is down")

    monkeypatch.setitem(sys.modules, "flare", BrokenFlare())
    notify_mod.flare("still needs saying", sev="page")  # must not raise
    assert "flare(page) failed" in capsys.readouterr().out


# -- fix 3: the daemon's liveness is observable from outside --------------- #

def test_serve_stamps_a_heartbeat_every_tick(tmp_path):
    pool = _pool(tmp_path)

    asyncio.run(pool.serve(exit_when_idle=True, interval=0.01))

    stamp = json.loads(pool.home.heartbeat_path().read_text())
    assert stamp["pid"] == os.getpid()
    assert stamp["ts"] and stamp["interval"] == 0.01


def test_heartbeat_write_failure_does_not_stop_serving(tmp_path, monkeypatch, capsys):
    pool = _pool(tmp_path)
    monkeypatch.setattr(pool.home, "heartbeat_path",
                        lambda: tmp_path / "absent-dir" / "daemon.heartbeat")

    asyncio.run(pool.serve(exit_when_idle=True, interval=0.01))

    assert "heartbeat write failed" in capsys.readouterr().out
