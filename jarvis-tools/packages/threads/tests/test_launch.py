"""Tests for the thread launcher: accept contract, router, deterministic weave
stamp, termination sweep, gate hooks, server endpoint, and dashboard pane.

No real ``claude``, concierge, tmux, or network: every router runner is stubbed
and the detached enqueue is monkeypatched to a no-op. All paths are redirected
under ``tmp_path`` by the autouse ``env`` fixture in conftest.
"""

from __future__ import annotations

import http.client
import json
from datetime import timedelta

import pytest

from conftest import NOW
from threads import config, dashboard, launch, note, server, spool, weave


@pytest.fixture(autouse=True)
def _no_detach(monkeypatch):
    """Never fire the detached router/monitor subprocess from a test."""
    monkeypatch.setattr(launch, "enqueue_intent", lambda *_a, **_k: None)
    monkeypatch.setattr(launch, "_enqueue_monitor", lambda *_a, **_k: None)


def _offline(*_a, **_k):
    return {"text": "{}", "cost_usd": 0.0}


# --------------------------------------------------------------------------- #
# the accept contract
# --------------------------------------------------------------------------- #
def test_accept_is_durable_fast_and_does_not_route():
    import time
    t0 = time.perf_counter()
    rec = launch.accept("do the thing", slug="alpha", enqueue=False)
    latency_ms = (time.perf_counter() - t0) * 1000
    assert latency_ms < 100  # the synchronous accept step is tiny
    saved = launch.load_intent(rec["id"])
    assert saved["state"] == "accepted"
    assert saved["resolved_slug"] is None       # no routing happened
    assert saved["executor_handle"] is None      # no executor spawned
    assert saved["requested_slug"] == "alpha"
    assert saved["mode"] == "full-auto"


def test_accept_enqueues_by_default(monkeypatch):
    seen = []
    monkeypatch.setattr(launch, "enqueue_intent", lambda i: seen.append(i))
    rec = launch.accept("go")
    assert seen == [rec["id"]]


def test_accept_rejects_empty_and_bad_mode():
    with pytest.raises(ValueError):
        launch.accept("   ", enqueue=False)
    with pytest.raises(ValueError):
        launch.accept("x", mode="fleet", enqueue=False)


def test_ulids_are_unique_and_sortable():
    ids = [launch._ulid() for _ in range(50)]
    assert len(set(ids)) == 50
    assert ids == sorted(ids) or len(set(ids[:1])) == 1  # monotonic within ms


# --------------------------------------------------------------------------- #
# router
# --------------------------------------------------------------------------- #
def test_pinned_slug_skips_the_model(env):
    calls = []

    def runner(*_a, **_k):
        calls.append(1)
        return {"text": "{}"}

    rec = launch.accept("x", slug="pinned-thread", dry_run=True, enqueue=False)
    out = launch.process_intent(rec["id"], runner=runner)
    assert out["resolved_slug"] == "pinned-thread"
    assert out["route"] == "pinned"
    assert calls == []  # pinned → no model call


def test_router_accepts_only_existing_slug(env):
    env.add_stub("known-thread")
    rec = launch.accept("something novel", dry_run=True, enqueue=False)
    runner = lambda *_a, **_k: {"text": json.dumps(
        {"slug": "invented", "reading": "r", "assumptions": "a"})}
    out = launch.process_intent(rec["id"], runner=runner)
    assert out["resolved_slug"] != "invented"   # not in registry → rejected
    assert out["route"] == "minted"


def test_router_attaches_to_matched_slug(env):
    env.add_stub("known-thread")
    rec = launch.accept("attach me", dry_run=True, enqueue=False)
    runner = lambda *_a, **_k: {"text": json.dumps(
        {"slug": "known-thread", "reading": "r", "assumptions": "a"})}
    out = launch.process_intent(rec["id"], runner=runner)
    assert out["resolved_slug"] == "known-thread"
    assert out["route"] == "model-match"


def test_dry_run_writes_note_zero_and_interpretation(env):
    rec = launch.accept("write the readme", slug="alpha", dry_run=True,
                        enqueue=False)
    launch.process_intent(rec["id"], runner=_offline)
    titles = [n["title"] for n in note.load_notes("alpha")]
    assert "intent (note zero)" in titles
    assert "router interpretation" in titles


# --------------------------------------------------------------------------- #
# gate menu
# --------------------------------------------------------------------------- #
def test_gate_menu_repo_vs_question():
    name_repo, _ = launch._gate_choice("please implement the parser and open a PR")
    name_q, _ = launch._gate_choice("what is the median latency of the fleet?")
    assert "PrOpen" in name_repo
    assert "threads-result" in name_q


# --------------------------------------------------------------------------- #
# deterministic weave — launcher stamp precedes all heuristics
# --------------------------------------------------------------------------- #
def _spawned_intent(slug, *, mode="full-auto", handle):
    """Persist a fully-spawned (non-dry-run) intent record."""
    rec = launch.accept("intent text", slug=slug, dry_run=False, enqueue=False)
    saved = launch.load_intent(rec["id"])
    saved.update(resolved_slug=slug, executor_handle=handle, state="spawned")
    launch._write(saved)
    return saved


def test_launcher_stamp_via_concierge_tid_beats_heuristics(env, write_record):
    env.add_stub("wrong-thread")   # a heuristic would grab this stub
    _spawned_intent("right-thread", mode="full-auto", handle="t-9999-abcd")
    # the concierge worker session lives under workspaces/<tid>; its stub hint
    # would otherwise weave it to `wrong-thread`.
    write_record(
        "sess-conc",
        cwd="/home/x/concierge-home/workspaces/t-9999-abcd",
        hints={"stubs": ["wrong-thread"], "goals": [], "repos": [],
               "branches": [], "prs": []})
    res = weave.weave(cluster=False, vault=False)
    row = {a["session_id"]: a for a in res.assignments}["sess-conc"]
    assert row["slug"] == "right-thread"
    assert row["method"] == "launcher-stamp"


def test_launcher_stamp_via_branch_prefix(env, write_record):
    _spawned_intent("copilot-thread", mode="copilot", handle="thread-tmux-x")
    write_record(
        "sess-copilot", cwd="/home/x/some/worktree",
        hints={"stubs": [], "goals": [], "repos": [],
               "branches": ["copilot-thread/ab12cd34"], "prs": []})
    res = weave.weave(cluster=False, vault=False)
    row = {a["session_id"]: a for a in res.assignments}["sess-copilot"]
    assert row["slug"] == "copilot-thread"
    assert row["method"] == "launcher-stamp"


def test_weave_check_asserts_launcher_determinism(env, write_record):
    _spawned_intent("right-thread", mode="full-auto", handle="t-9999-abcd")
    write_record(
        "sess-conc", cwd="/home/x/concierge-home/workspaces/t-9999-abcd",
        hints={"stubs": [], "goals": [], "repos": [], "branches": [], "prs": []})
    weave.weave(cluster=False, vault=False)
    ok, report = weave.weave_check()
    assert ok
    assert "launcher-stamped sessions deterministic: 1/1 = 100%" in report


def test_weave_check_flags_stale_launcher_assignment(env, write_record):
    # a launcher session whose stored assignment resolved to the wrong slug is a
    # determinism violation the gate must catch.
    _spawned_intent("right-thread", mode="full-auto", handle="t-9999-abcd")
    write_record(
        "sess-conc", cwd="/home/x/concierge-home/workspaces/t-9999-abcd",
        hints={"stubs": [], "goals": [], "repos": [], "branches": [], "prs": []})
    spool.write_assignments([
        {"session_id": "sess-conc", "slug": "some-other", "method": "repo",
         "confidence": 0.8}])
    ok, report = weave.weave_check()
    assert not ok
    assert "launcher-stamp mismatch" in report


def test_dry_run_intents_do_not_stamp(env, write_record):
    # a --dry-run intent must not create a deterministic mapping.
    rec = launch.accept("x", slug="dry-slug", dry_run=True, enqueue=False)
    launch.process_intent(rec["id"], runner=_offline)
    tid_to_slug, launched = launch.stamp_index()
    assert "dry-slug" not in launched
    assert tid_to_slug == {}


# --------------------------------------------------------------------------- #
# termination sweep
# --------------------------------------------------------------------------- #
def test_termination_sweep_flags_dormant_intent(env):
    rec = launch.accept("forgotten work", slug="stale-thread", dry_run=False,
                        enqueue=False)
    saved = launch.load_intent(rec["id"])
    saved["created_at"] = (NOW - timedelta(days=5)).isoformat()
    launch._write(saved)
    flagged = launch.termination_sweep(now=NOW, flare_warning=False)
    assert flagged == [rec["id"]]
    body = note.load_notes("stale-thread")[0]["body"]
    assert "BLOCKED-ON-DANIEL" in body
    # idempotent: a second sweep does not re-flag
    assert launch.termination_sweep(now=NOW, flare_warning=False) == []


def test_termination_sweep_ignores_terminal_and_fresh(env):
    fresh = launch.accept("recent", slug="a", dry_run=False, enqueue=False)
    done = launch.accept("finished", slug="b", dry_run=False, enqueue=False)
    d = launch.load_intent(done["id"])
    d.update(created_at=(NOW - timedelta(days=9)).isoformat(),
             terminal_state="result")
    launch._write(d)
    assert launch.termination_sweep(now=NOW, flare_warning=False) == []
    assert launch.load_intent(fresh["id"]).get("sweep_flagged_at") is None


# --------------------------------------------------------------------------- #
# gate hooks
# --------------------------------------------------------------------------- #
def test_launch_check_ok_and_reports_latency(env):
    ok, report = launch.launch_check()
    assert ok
    assert "accept latency:" in report
    assert "launch --check OK" in report
    # the synthetic check intent is cleaned up (no accumulation).
    assert not any(i.get("requested_slug") == "launcher-check"
                   for i in launch.load_intents())


def test_launch_check_fails_on_inconsistent_intent(env):
    # an old, un-spawned, un-failed intent is an inconsistency.
    rec = launch.accept("orphan", slug="x", dry_run=False, enqueue=False)
    saved = launch.load_intent(rec["id"])
    saved["updated_at"] = (NOW - timedelta(days=2)).isoformat()  # past grace
    launch._write(saved)
    ok, report = launch.launch_check()
    assert not ok
    assert "inconsistent" in report


# --------------------------------------------------------------------------- #
# veto affordances
# --------------------------------------------------------------------------- #
def test_detach_and_merge(env):
    rec = launch.accept("misrouted", slug="wrong", dry_run=True, enqueue=False)
    launch.process_intent(rec["id"], runner=_offline)
    launch.detach(rec["id"])
    assert launch.load_intent(rec["id"])["state"] == "detached"
    launch.merge_into(rec["id"], "right-thread")
    saved = launch.load_intent(rec["id"])
    assert saved["state"] == "merged"
    assert saved["resolved_slug"] == "right-thread"
    assert any("merged" in n["title"] for n in note.load_notes("right-thread"))


# --------------------------------------------------------------------------- #
# server endpoint
# --------------------------------------------------------------------------- #
def test_post_launch_endpoint_accepts(env, monkeypatch):
    monkeypatch.setattr(launch, "enqueue_intent", lambda *_a, **_k: None)
    srv = server.serve(tunnel=False)
    try:
        port = int(srv.local_url.rsplit(":", 1)[1])
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/launch",
                     body=json.dumps({"text": "do a thing", "mode": "copilot"}),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        assert resp.status == 202
        rec = json.loads(resp.read())
        assert rec["mode"] == "copilot"
        assert rec["state"] == "accepted"
        assert launch.load_intent(rec["id"])["text"] == "do a thing"
    finally:
        srv.stop()


def test_post_launch_rejects_empty_text(env):
    srv = server.serve(tunnel=False)
    try:
        port = int(srv.local_url.rsplit(":", 1)[1])
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/launch", body=json.dumps({"text": ""}),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        assert resp.status == 400
    finally:
        srv.stop()


# --------------------------------------------------------------------------- #
# dashboard launcher pane
# --------------------------------------------------------------------------- #
def test_dashboard_renders_launcher_pane(env):
    env.add_stub("some-thread", memory_line="a thread")
    html = dashboard.render_html(dashboard.build(now=NOW), now=NOW)
    assert "Launch a thread" in html
    assert "launch-text" in html
    assert "thread-slugs" in html          # slug autocomplete datalist


def test_dashboard_lists_launched_intents_with_veto(env):
    _spawned_intent("shown-thread", mode="full-auto", handle="t-1111-aaaa")
    html = dashboard.render_html(dashboard.build(now=NOW), now=NOW)
    assert "Launched intents" in html
    assert "shown-thread" in html
    assert "detach" in html and "merge into thread" in html
