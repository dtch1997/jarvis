"""The auto-wrapup backstop: classification, offline evidence, the report,
idempotence, dispatch caps, and the ``--verify`` gate.

No model, no network, no concierge daemon: the summarizer runner raises if
anything reaches for it, ``gh`` is replaced by a canned prober, and the
dispatch submitter is a list append. The git plumbing under test is real git
against a temp repo whose "remote" is a bare repo on disk.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from conftest import NOW
from threads import config, note, spool, summarize, sweep
from threads.cli import main


@pytest.fixture(autouse=True)
def _no_model(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("the sweep must never make a model call")
    monkeypatch.setattr(summarize, "default_runner", boom)


@pytest.fixture
def repo(tmp_path):
    return sweep._fixture_repo(tmp_path / "git")


def _thread(slug, *, days_ago, status="", cwd="", branch="", body="body",
            signals=(), session_days_ago=None):
    sweep._fixture_thread(slug, days_ago=days_ago, status=status, cwd=cwd,
                          branch=branch, body=body, now=NOW, signals=signals,
                          session_days_ago=session_days_ago)


def _run(**kw):
    kw.setdefault("now", NOW)
    kw.setdefault("prober", sweep._NoNetworkProber())
    kw.setdefault("write", False)
    kw.setdefault("flare_info", False)
    return sweep.sweep(**kw)


def _cls(result):
    return {c.slug: c.cls for c in result.candidates}


# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #
def test_classifies_every_thread_into_one_bucket(env, repo):
    _thread("done-thread", days_ago=30, status="done")
    _thread("blocked-thread", days_ago=30, status="blocked",
            body="BLOCKED-ON-DANIEL: which bucket?")
    _thread("parked-old", days_ago=40, status="parked")
    _thread("parked-grace", days_ago=10, status="parked")
    _thread("fresh", days_ago=1, status="ongoing")
    res = _run()
    assert _cls(res) == {"done-thread": "terminal", "blocked-thread": "blocked",
                         "parked-old": "B", "parked-grace": "fresh",
                         "fresh": "fresh"}
    assert sum(res.counts.values()) == res.threads == 5
    assert set(res.counts) <= set(sweep.CLASSES)


def test_stale_boundary_is_the_configured_horizon(env):
    _thread("edge", days_ago=8, status="")
    assert _cls(_run())["edge"] != "fresh"
    from dataclasses import replace
    cfg = config.load_config()
    wide = replace(cfg, sweep=replace(cfg.sweep, stale_days=30))
    assert _cls(_run(cfg=wide))["edge"] == "fresh"


def test_closed_stub_is_terminal_even_without_a_note(env):
    env.add_stub("shipped", memory_line="wrapped up and retired")
    _thread("shipped", days_ago=40, status="ongoing")
    assert _cls(_run())["shipped"] == "terminal"


def test_note_older_than_the_last_session_does_not_speak_for_the_thread(env):
    """A parked note, then more work, then silence → A, not parked."""
    _thread("moved-on", days_ago=30, status="parked", session_days_ago=20)
    assert _cls(_run())["moved-on"] in ("A1", "A2", "B")


def test_abandoned_midstream_signal_makes_it_a_candidate(env, repo):
    sweep._fixture_branch(repo, "abandoned/work", commits=1)
    _thread("abandoned", days_ago=20, status="", cwd=str(repo),
            branch="abandoned/work", session_days_ago=20,
            signals=("abandoned-midstream",))
    res = _run()
    assert _cls(res)["abandoned"] == "A1"
    assert "abandoned-midstream" in res.candidates[0].trigger
    assert "abandoned-midstream" in res.report_text


def test_exempt_slugs_are_never_swept(env):
    from dataclasses import replace
    _thread("dormant-on-purpose", days_ago=99, status="")
    cfg = config.load_config()
    cfg = replace(cfg, sweep=replace(cfg.sweep, exempt=("dormant-on-purpose",)))
    res = _run(cfg=cfg)
    assert res.threads == 0 and res.exempt == ["dormant-on-purpose"]


def test_never_started_capture_gets_a_close_or_shelve_disposition(env):
    _thread("captured-idea", days_ago=40, status="")
    cand = _run().candidates[0]
    assert cand.cls == "B" and cand.never_started
    assert "never picked up" in cand.disposition


# --------------------------------------------------------------------------- #
# offline evidence (real git, canned gh)
# --------------------------------------------------------------------------- #
def test_a1_unpushed_commits(env, repo):
    sweep._fixture_branch(repo, "a1/work", commits=2)
    _thread("a1", days_ago=0, body="", cwd=str(repo),
            branch="a1/work", session_days_ago=20)
    cand = _run().candidates[0]
    assert cand.cls == "A1"
    assert cand.branches[0].unpushed == 2 and cand.branches[0].novel == 2


def test_a2_dirty_worktree_is_report_only(env, repo, tmp_path):
    sweep._fixture_branch(repo, "a2/work", commits=1, push=True)
    wt = tmp_path / "wt"
    sweep._git(repo, "worktree", "add", "-q", str(wt), "a2/work")
    (wt / "mid-edit.py").write_text("x = 1\n")
    _thread("a2", days_ago=0, body="", cwd=str(repo),
            branch="a2/work", session_days_ago=20)
    cand = _run().candidates[0]
    assert cand.cls == "A2" and cand.branches[0].dirty == 1
    assert str(wt) in cand.reason


def test_merged_pr_is_not_stranded_work(env, repo):
    """gazette squash-merges, so a merged branch keeps commits trunk lacks —
    that must not read as un-PR'd work forever."""
    sweep._fixture_branch(repo, "merged/work", commits=1, push=True)
    _thread("merged", days_ago=0, body="", cwd=str(repo),
            branch="merged/work", session_days_ago=20)
    prober = sweep._NoNetworkProber(
        {"merged/work": ("https://x.invalid/pr/1", "MERGED")})
    cand = _run(prober=prober).candidates[0]
    assert cand.branches[0].novel == 1 and not cand.branches[0].at_risk
    assert cand.cls == "B"


def test_open_pr_with_no_parking_note_is_a1(env, repo):
    sweep._fixture_branch(repo, "openpr/work", commits=1, push=True)
    _thread("openpr", days_ago=0, body="", cwd=str(repo),
            branch="openpr/work", session_days_ago=20)
    prober = sweep._NoNetworkProber({"openpr/work": "https://x.invalid/pr/2"})
    cand = _run(prober=prober).candidates[0]
    assert cand.cls == "A1" and "PR open" in cand.reason


def test_a_note_branch_from_another_workspace_is_not_this_threads_work(env, repo):
    """One worker parking notes onto many threads must not hand them all its
    own branch (that produced 46 bogus A1s on the real spool)."""
    sweep._fixture_branch(repo, "pool/t-0818-bf5d", commits=1)
    _thread("someone-elses-branch", days_ago=20, status="", cwd=str(repo),
            branch="pool/t-0818-bf5d")
    res = _run()
    assert res.candidates[0].branches == []
    assert res.candidates[0].cls == "B"
    assert not sweep.branch_corroborates("pool/t-0818-bf5d", "unrelated-slug")
    assert sweep.branch_corroborates("pool/threads-sweep", "threads-sweep-work")
    assert sweep.branch_corroborates("myslug/01ABC", "myslug")


def test_a_branch_claimed_by_many_threads_is_ignored(env, repo):
    sweep._fixture_branch(repo, "shared/work", commits=1)
    for i in range(5):
        _thread(f"shared-work-{i}", days_ago=0, body="", cwd=str(repo),
                branch="shared/work", session_days_ago=20)
    res = _run()
    assert all(not c.branches for c in res.candidates)
    assert any("claimed by more than" in t for t in res.truncated)


def test_trunk_branches_are_never_treated_as_work(env, repo):
    _thread("on-main", days_ago=0, body="", cwd=str(repo),
            branch="main", session_days_ago=20)
    assert _run().candidates[0].branches == []


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def test_report_shows_branch_unpushed_count_and_pr_state(env, repo):
    sweep._fixture_branch(repo, "ev/work", commits=3)
    _thread("ev", days_ago=0, body="", cwd=str(repo),
            branch="ev/work", session_days_ago=20)
    text = _run().report_text
    assert "ev/work" in text and "3 unpushed commit(s)" in text
    assert "no PR" in text and "stale 20d" in text


def test_idle_run_still_appends_a_log_line_and_writes_no_report(env):
    _thread("fresh", days_ago=1, status="ongoing")
    res = _run(write=True)
    assert res.report_path is None
    rows = [json.loads(ln) for ln in
            config.sweep_log_path().read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["counts"]["fresh"] == 1


def test_rerun_is_a_noop(env, repo):
    sweep._fixture_branch(repo, "again/work", commits=1)
    _thread("again", days_ago=0, body="", cwd=str(repo),
            branch="again/work", session_days_ago=20)
    first = _run(write=True)
    before = first.report_path.read_text()
    notes_before = sorted(p.name for p in config.notes_dir().rglob("*.md"))
    second = _run(now=NOW + timedelta(minutes=7), write=True)
    assert second.report_path.read_text() == before
    assert sorted(p.name for p in config.notes_dir().rglob("*.md")) == notes_before
    assert len(config.sweep_log_path().read_text().splitlines()) == 2


def test_a_long_b_section_keeps_every_thread_but_bounds_the_detail(env):
    for i in range(sweep.MAX_DETAILED_PER_SECTION + 5):
        _thread(f"capture-{i:03d}", days_ago=40 + i, status="")
    res = _run()
    text = res.report_text
    assert res.counts["B"] == sweep.MAX_DETAILED_PER_SECTION + 5
    assert "more B thread(s), one line each" in text
    for i in range(sweep.MAX_DETAILED_PER_SECTION + 5):
        assert f"capture-{i:03d}" in text          # nothing silently dropped


def test_the_sweep_never_writes_a_note_onto_a_thread(env, repo):
    sweep._fixture_branch(repo, "quiet/work", commits=1)
    _thread("quiet", days_ago=0, body="", cwd=str(repo),
            branch="quiet/work", session_days_ago=20)
    before = sorted(p.name for p in config.notes_dir().rglob("*.md"))
    _run(write=True)
    assert sorted(p.name for p in config.notes_dir().rglob("*.md")) == before


# --------------------------------------------------------------------------- #
# dispatch (config-gated, off by default)
# --------------------------------------------------------------------------- #
def _dispatch_cfg(**kw):
    from dataclasses import replace
    cfg = config.load_config()
    return replace(cfg, sweep=replace(cfg.sweep, mode="dispatch", **kw))


def test_report_mode_dispatches_nothing(env, repo):
    sweep._fixture_branch(repo, "rm/work", commits=1)
    _thread("rm", days_ago=0, body="", cwd=str(repo),
            branch="rm/work", session_days_ago=20)
    res = _run(write=True)
    assert res.mode == "report" and res.dispatched == []
    assert not config.sweep_state_path().exists()


def test_dispatch_respects_the_per_run_cap_and_skips_a2_and_b(env, repo, tmp_path):
    for i in range(3):
        sweep._fixture_branch(repo, f"d{i}/work", commits=1)
        _thread(f"d{i}", days_ago=0, body="", cwd=str(repo),
                branch=f"d{i}/work", session_days_ago=20)
    sweep._fixture_branch(repo, "dirty/work", commits=1, push=True)
    wt = tmp_path / "wt2"
    sweep._git(repo, "worktree", "add", "-q", str(wt), "dirty/work")
    (wt / "edit.py").write_text("x\n")
    _thread("dirty", days_ago=0, body="", cwd=str(repo),
            branch="dirty/work", session_days_ago=20)
    _thread("parked-old", days_ago=40, status="parked")

    sent = []

    def submit(**kw):
        sent.append(kw)
        return f"t-{len(sent)}"

    res = _run(cfg=_dispatch_cfg(max_dispatch_per_run=2), write=True,
               submitter=submit)
    assert len(sent) == 2 and len(res.dispatched) == 2
    assert {d["slug"] for d in res.dispatched} <= {"d0", "d1", "d2"}
    assert all(k["gate_cmd"].startswith("threads sweep --verify") for k in sent)
    assert all(k["pr_gate"] for k in sent)          # novel commits, no PR
    assert "never merge anything" in sent[0]["spec"]
    state = json.loads(config.sweep_state_path().read_text())
    assert len(state["dispatches"]) == 2


def test_a_pending_dispatch_blocks_a_redispatch(env, repo):
    sweep._fixture_branch(repo, "p/work", commits=1)
    _thread("p", days_ago=0, body="", cwd=str(repo),
            branch="p/work", session_days_ago=20)
    sent = []
    _run(cfg=_dispatch_cfg(), write=True,
         submitter=lambda **kw: (sent.append(kw), "t-pending")[1])
    env.add_task("t-pending")            # no status field → treated as pending
    res2 = _run(cfg=_dispatch_cfg(), write=True, now=NOW + timedelta(days=1),
                submitter=lambda **kw: (sent.append(kw), "t-again")[1])
    assert res2.dispatched == [] and len(sent) == 1
    assert "pending" in res2.candidates[0].dispatch_skip


def test_a_failed_dispatch_holds_the_cooldown_then_retries(env, repo):
    sweep._fixture_branch(repo, "c/work", commits=1)
    _thread("c", days_ago=0, body="", cwd=str(repo),
            branch="c/work", session_days_ago=20)
    _run(cfg=_dispatch_cfg(), write=True, submitter=lambda **kw: "t-failed")
    (env.concierge / "tasks" / "t-failed.json").write_text(
        json.dumps({"id": "t-failed", "status": "failed"}))
    inside = _run(cfg=_dispatch_cfg(cooldown_days=7), write=True,
                  now=NOW + timedelta(days=2), submitter=lambda **kw: "t-2")
    assert inside.dispatched == [] and "cooldown" in inside.candidates[0].dispatch_skip
    after = _run(cfg=_dispatch_cfg(cooldown_days=7), write=True,
                 now=NOW + timedelta(days=9), submitter=lambda **kw: "t-2")
    assert [d["slug"] for d in after.dispatched] == ["c"]


def test_a_dispatch_failure_is_a_blocked_on_daniel_report_line(env, repo):
    sweep._fixture_branch(repo, "f/work", commits=1)
    _thread("f", days_ago=0, body="", cwd=str(repo),
            branch="f/work", session_days_ago=20)

    def refuse(**_kw):
        raise RuntimeError("pool unreachable")

    res = _run(cfg=_dispatch_cfg(), write=True, submitter=refuse)
    assert res.dispatched == []
    assert "BLOCKED-ON-DANIEL" in res.report_text
    assert "pool unreachable" in res.candidates[0].dispatch_skip


def test_the_real_submitter_refuses_when_enqueue_is_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("THREADS_DISABLE_ENQUEUE", "1")
    with pytest.raises(RuntimeError, match="THREADS_DISABLE_ENQUEUE"):
        sweep.default_submitter(spec="s", title="t", repo=str(tmp_path),
                                branch="b", gate_cmd="true", pr_gate=False,
                                budget_usd=1.0)


# --------------------------------------------------------------------------- #
# --verify, the concierge gate
# --------------------------------------------------------------------------- #
def test_verify_fails_on_an_unwrapped_thread_and_passes_once_wrapped(env, repo):
    sweep._fixture_branch(repo, "v/work", commits=1)
    _thread("v", days_ago=0, body="", cwd=str(repo),
            branch="v/work", session_days_ago=20)
    since = NOW - timedelta(days=1)
    ok, text = sweep.verify("v", now=NOW, prober=sweep._NoNetworkProber(),
                            since=since)
    assert not ok and "unpushed" in text

    sweep._git(repo, "push", "-q", "origin", "v/work")
    note.add_note("v", "pushed, PR up, parking", title="wrapped",
                  status="parked", cwd=str(repo), branch="v/work", now=NOW)
    prober = sweep._NoNetworkProber({"v/work": "https://x.invalid/pr/5"})
    ok, text = sweep.verify("v", now=NOW + timedelta(minutes=1), prober=prober,
                            since=since)
    assert ok, text


def test_verify_needs_a_note_newer_than_the_dispatch(env, repo):
    sweep._fixture_branch(repo, "stale-note/work", commits=1, push=True)
    _thread("stale-note", days_ago=20, status="parked", cwd=str(repo),
            branch="stale-note/work", session_days_ago=25)
    prober = sweep._NoNetworkProber({"stale-note/work": "https://x.invalid/pr/6"})
    ok, text = sweep.verify("stale-note", now=NOW, prober=prober,
                            since=NOW - timedelta(days=1))
    assert not ok and "note newer than" in text


def test_verify_rejects_novel_commits_with_no_pr(env, repo):
    sweep._fixture_branch(repo, "nopr/work", commits=1, push=True)
    _thread("nopr", days_ago=1, status="parked", cwd=str(repo),
            branch="nopr/work", session_days_ago=2)
    ok, text = sweep.verify("nopr", now=NOW, prober=sweep._NoNetworkProber(),
                            since=NOW - timedelta(days=1.5))
    assert not ok and "need a PR" in text


def test_verify_accepts_an_already_merged_pr(env, repo):
    sweep._fixture_branch(repo, "gone/work", commits=1, push=True)
    _thread("gone", days_ago=1, status="parked", cwd=str(repo),
            branch="gone/work", session_days_ago=2)
    prober = sweep._NoNetworkProber(
        {"gone/work": ("https://x.invalid/pr/4", "MERGED")})
    ok, text = sweep.verify("gone", now=NOW, prober=prober,
                            since=NOW - timedelta(days=1.5))
    assert ok, text


def test_verify_fails_closed_on_an_unknown_slug(env):
    ok, text = sweep.verify("never-heard-of-it", now=NOW,
                            prober=sweep._NoNetworkProber())
    assert not ok and "no such thread" in text


# --------------------------------------------------------------------------- #
# CLI + the offline gate
# --------------------------------------------------------------------------- #
def test_cli_dry_run_prints_the_report_and_writes_nothing(env, capsys, repo):
    sweep._fixture_branch(repo, "cli/work", commits=1)
    _thread("cli", days_ago=0, body="", cwd=str(repo),
            branch="cli/work", session_days_ago=20)
    assert main(["sweep", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "threads sweep —" in out and "cli/work" in out
    assert not config.sweep_dir().exists()


def test_cli_verify_exit_codes(env, capsys, repo):
    sweep._fixture_branch(repo, "x/work", commits=1)
    _thread("x", days_ago=0, body="", cwd=str(repo),
            branch="x/work", session_days_ago=20)
    assert main(["sweep", "--verify", "x"]) == 1
    assert main(["sweep", "--verify", "nope-not-here"]) == 1


def test_cli_stale_days_override(env, capsys):
    _thread("recent", days_ago=3, status="")
    assert main(["sweep", "--dry-run"]) == 0
    assert "0 A1" in capsys.readouterr().out
    assert main(["sweep", "--dry-run", "--stale-days", "1"]) == 0
    assert "1 B" in capsys.readouterr().out


def test_sweep_check_is_hermetic_and_passes(env, capsys, monkeypatch):
    """The gate itself: it must pass, write nothing to the (fixture) real
    spool, and never touch the network."""
    real_run = sweep.Prober.run

    def no_network(self, args, **kw):
        assert args and args[0] != "gh", "--check must never invoke gh"
        return real_run(self, args, **kw)

    monkeypatch.setattr(sweep.Prober, "run", no_network)
    _thread("something", days_ago=20, status="ongoing")
    before = sweep._listing(config.sweep_dir())
    assert main(["sweep", "--check"]) == 0
    assert sweep._listing(config.sweep_dir()) == before
    assert "0 failed" in capsys.readouterr().out
