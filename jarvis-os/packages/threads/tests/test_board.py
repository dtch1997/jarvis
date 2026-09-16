"""The thread board: row model, Goal cell (draft → edit → gate), Status
derivation for every lifecycle state, needs-you sort, serving, and the gate.

No model, no network beyond localhost, no real concierge daemon: task records
are written as fixture JSON (the shape ``concierge.records.new_task`` produces)
and the detached router/monitor subprocesses are monkeypatched away.
"""

from __future__ import annotations

import http.client
import json
from datetime import timedelta

import pytest

from conftest import NOW
from threads import board, config, dashboard, launch, note, server, summarize
from threads.cli import main


@pytest.fixture(autouse=True)
def _no_detach(monkeypatch):
    monkeypatch.setattr(launch, "enqueue_intent", lambda *_a, **_k: None)
    monkeypatch.setattr(launch, "_enqueue_monitor", lambda *_a, **_k: None)


def _offline(*_a, **_k):
    return {"text": "{}", "cost_usd": 0.0}


# captured before the autouse fixture stubs it out
_REAL_ENQUEUE = launch.enqueue_intent


def _task(env, tid, *, status="running", detail="", attempts=1, cost=0.0,
          gate_passed=None, links=None, result_text="", updated=None,
          budget_usd=20.0):
    """Write a concierge task record with the fields the board reads."""
    task = {
        "id": tid, "title": f"thread launch: {tid}",
        "workspace": {"repo": "/tmp/repo", "branch": f"b/{tid}"},
        "budget": {"usd": budget_usd, "wall_minutes": 240.0},
        "status": status, "status_detail": detail,
        "attempts": [{"n": i + 1, "cost_usd": cost} for i in range(attempts)],
        "max_attempts": 3, "result_text": result_text,
        "links": links or {"pr": None, "report": None, "dashboard": None},
        "gate_result": (None if gate_passed is None
                        else {"passed": gate_passed, "detail": f"verdict {tid}"}),
        "created": (NOW - timedelta(hours=2)).isoformat(),
        "updated": (updated or NOW).isoformat(),
    }
    d = env.concierge / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{tid}.json").write_text(json.dumps(task))
    return task


def _intent(text="do the thing", *, slug="alpha", tid=None, state="spawned",
            terminal=None, updated=None, flagged=None, mode="full-auto",
            goal=None):
    rec = launch.accept(text, mode=mode, slug=slug, enqueue=False)
    saved = launch.load_intent(rec["id"])
    saved.update(resolved_slug=slug, route="pinned", state=state,
                 executor_handle=tid, terminal_state=terminal,
                 goal=goal or launch.fallback_goal(text,
                                                   launch.gate_spec_for(saved)),
                 goal_state=launch.GOAL_DRAFTED)
    if updated:
        saved["created_at"] = saved["updated_at"] = updated.isoformat()
    if flagged:
        saved["sweep_flagged_at"] = flagged.isoformat()
    launch._write(saved)
    return saved


# --------------------------------------------------------------------------- #
# Status column — derived from observed state, one case per lifecycle value
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pool_status,expected", [
    ("queued", "spawning"), ("held", "spawning"), ("running", "running"),
    ("waiting", "running"), ("blocked", "blocked"), ("done", "result"),
    ("failed", "failed"), ("cancelled", "failed"),
])
def test_lifecycle_from_pool_status(env, pool_status, expected):
    _task(env, "t-1", status=pool_status)
    rec = _intent(tid="t-1")
    st = board.status_fields(rec, launch.read_task("t-1"), now=NOW)
    assert st["lifecycle"] == expected


def test_lifecycle_routing_then_spawning_then_running(env):
    accepted = launch.accept("route me", slug="a", enqueue=False)
    assert board.status_fields(accepted, None, now=NOW)["lifecycle"] == "routing"
    routed = dict(accepted, state="routed", resolved_slug="a")
    assert board.status_fields(routed, None, now=NOW)["lifecycle"] == "routing"
    # a handle with no task record yet (submitted, daemon has not written it)
    spawned = dict(routed, state="routed", executor_handle="t-nope")
    assert board.status_fields(spawned, None, now=NOW)["lifecycle"] == "spawning"
    live = dict(spawned, state="spawned")
    assert board.status_fields(live, None, now=NOW)["lifecycle"] == "running"


def test_terminal_state_without_task_record(env):
    rec = _intent(tid=None, state="terminal", terminal="blocked")
    assert board.status_fields(rec, None, now=NOW)["lifecycle"] == "blocked"


def test_running_row_carries_pool_status_attempt_and_cost(env):
    _task(env, "t-run", status="running", attempts=2, cost=0.21, budget_usd=5.0)
    rec = _intent(tid="t-run")
    st = board.status_fields(rec, launch.read_task("t-run"), now=NOW)
    assert st["pool"]["status"] == "running"
    assert st["pool"]["attempt"] == 2
    assert st["pool"]["cost_usd"] == pytest.approx(0.42)
    assert st["pool"]["budget_usd"] == 5.0


def test_blocked_row_renders_the_actual_question(env):
    question = "Which GCS bucket should the eval dumps go to?"
    _task(env, "t-b", status="blocked", detail=question)
    rec = _intent(tid="t-b")
    row = board.launched_row(rec, now=NOW, cfg=config.Config(), notes_by_slug={})
    assert row.lifecycle == "blocked" and row.needs_you
    assert question in board._status_cell(row, NOW)


def test_result_row_renders_deliverable_pointers_inline(env):
    _task(env, "t-done", status="done", gate_passed=True, detail="shell_ok rc=0",
          links={"pr": "https://example.invalid/pr/7",
                 "report": "https://example.invalid/report"})
    rec = _intent(tid="t-done", state="terminal", terminal="result")
    row = board.launched_row(rec, now=NOW, cfg=config.Config(), notes_by_slug={})
    cell = board._status_cell(row, NOW)
    assert "https://example.invalid/pr/7" in cell
    assert "https://example.invalid/report" in cell
    assert "verdict t-done" in cell          # the gate's own verdict


def test_status_column_never_shows_worker_self_report(env):
    token = "I-AM-DONE-TRUST-ME"
    _task(env, "t-p", status="done", gate_passed=True, detail="shell_ok rc=0",
          result_text=token)
    rec = _intent(tid="t-p", state="terminal", terminal="result")
    st = board.status_fields(rec, launch.read_task("t-p"), now=NOW)
    row = board.launched_row(rec, now=NOW, cfg=config.Config(), notes_by_slug={})
    assert token not in json.dumps(st, default=str)
    assert token not in board._status_cell(row, NOW)
    assert token not in board.render_html(board.build(now=NOW, sweep=False))


def test_contract_violation_is_loud_and_needs_you(env):
    rec = _intent(tid=None, state="routed", flagged=NOW)
    row = board.launched_row(rec, now=NOW, cfg=config.Config(), notes_by_slug={})
    assert row.violation and row.needs_you and not row.archived
    page = board.render_html(board.build(now=NOW, sweep=False))
    assert "TERMINATION CONTRACT VIOLATED" in page


def test_deepest_live_link_prefers_dashboard_then_foyer_then_log_tail(env):
    _task(env, "t-flow", status="running",
          links={"dashboard": "https://example.invalid/stagehand"})
    rec = _intent(tid="t-flow")
    st = board.status_fields(rec, launch.read_task("t-flow"), now=NOW)
    assert st["live"] == ("stagehand dashboard", "https://example.invalid/stagehand")

    copilot = dict(_intent("pair up", slug="cop", tid="thread-cop-1",
                           mode="copilot"),
                   foyer_url="https://foyer.invalid/t")
    st = board.status_fields(copilot, None, now=NOW)
    assert st["live"] == ("foyer terminal", "https://foyer.invalid/t")

    _task(env, "t-log", status="running")
    (env.concierge / "logs" / "t-log" / "attempt-1").mkdir(parents=True)
    (env.concierge / "logs" / "t-log" / "attempt-1" / "agent.jsonl").write_text(
        "line one\nline two\n")
    st = board.status_fields(_intent(tid="t-log", slug="l"),
                             launch.read_task("t-log"), now=NOW)
    assert st["live"] == ("log tail", "tail?tid=t-log")
    assert "line two" in board.log_tail("t-log")


# --------------------------------------------------------------------------- #
# rows: launched + observed
# --------------------------------------------------------------------------- #
def test_observed_threads_appear_as_marked_rows(env, write_record, canned_runner):
    from threads import weave
    env.add_stub("safety-desert", body="repos/safety-desert")
    write_record("s1", hints={"stubs": [], "goals": [], "repos": ["safety-desert"],
                              "branches": [], "prs": []})
    weave.weave(runner=canned_runner, cluster=False, vault=False)
    b = board.build(now=NOW, sweep=False)
    row = next(r for r in b.rows if r.slug == "safety-desert")
    assert row.kind == "observed" and row.lifecycle == "active"
    assert not row.editable_goal          # no launcher goal to edit
    page = board.render_html(b)
    assert ">observed<" in page            # visually marked as observed


def test_parked_observed_thread_archives_and_blocked_one_pins(env):
    note.add_note("parked-thread", "context dump", status="parked", now=NOW)
    note.add_note("stuck-thread", "BLOCKED-ON-DANIEL: which bucket?",
                  status="blocked", now=NOW)
    b = board.build(now=NOW, sweep=False)
    by = {r.slug: r for r in b.rows}
    assert by["parked-thread"].lifecycle == "parked"
    assert by["parked-thread"].archived        # nothing in flight to monitor
    assert by["stuck-thread"].lifecycle == "blocked"
    assert by["stuck-thread"].needs_you and not by["stuck-thread"].archived
    assert b.live[0].slug == "stuck-thread"   # needs-you first


def test_launched_row_replaces_its_observed_twin(env):
    """A launched thread also has notes, so it must appear exactly once."""
    rec = _intent("launched work", slug="dup-thread", tid=None, state="routed")
    note.add_note("dup-thread", rec["text"], title="intent (note zero)", now=NOW)
    b = board.build(now=NOW, sweep=False)
    rows = [r for r in b.rows if r.slug == "dup-thread"]
    assert len(rows) == 1 and rows[0].kind == "launched"


# --------------------------------------------------------------------------- #
# sort + archive
# --------------------------------------------------------------------------- #
def test_needs_you_first_then_running_by_recency_then_terminal(env):
    old = NOW - timedelta(days=30)
    _task(env, "t-viol", status="running", updated=old)
    _task(env, "t-block", status="blocked", detail="decide?",
          updated=NOW - timedelta(hours=6))
    _task(env, "t-fresh", status="running", updated=NOW - timedelta(minutes=1))
    _task(env, "t-stale", status="running", updated=NOW - timedelta(hours=8))
    _task(env, "t-old-done", status="done", gate_passed=True, updated=old)
    _intent("violating", slug="s-viol", tid="t-viol", updated=old, flagged=NOW)
    _intent("blocked", slug="s-block", tid="t-block",
            updated=NOW - timedelta(hours=6))
    _intent("fresh", slug="s-fresh", tid="t-fresh",
            updated=NOW - timedelta(minutes=1))
    _intent("stale", slug="s-stale", tid="t-stale",
            updated=NOW - timedelta(hours=8))
    _intent("settled", slug="s-done", tid="t-old-done", state="terminal",
            terminal="result", updated=old)
    b = board.build(now=NOW, sweep=False)
    assert [r.slug for r in b.live] == ["s-viol", "s-block", "s-fresh", "s-stale"]
    assert [r.slug for r in b.archive] == ["s-done"]


def test_archive_days_is_configurable(env):
    settled = NOW - timedelta(days=4)
    _task(env, "t-4d", status="done", gate_passed=True, updated=settled)
    _intent("four days old", slug="s-4d", tid="t-4d", state="terminal",
            terminal="result", updated=settled)
    keep = board.build(now=NOW, cfg=config.Config(board_archive_days=7),
                       sweep=False)
    assert [r.slug for r in keep.live] == ["s-4d"]
    collapse = board.build(now=NOW, cfg=config.Config(board_archive_days=1),
                           sweep=False)
    assert [r.slug for r in collapse.archive] == ["s-4d"]
    assert "archive —" in board.render_html(collapse)


def test_launched_rows_sort_above_observed_on_a_tie(env):
    _task(env, "t-l", status="running", updated=NOW)
    _intent("launched now", slug="s-launched", tid="t-l", updated=NOW)
    note.add_note("s-observed", "active thread", now=NOW)
    b = board.build(now=NOW, sweep=False)
    assert b.live[0].slug == "s-launched"


# --------------------------------------------------------------------------- #
# Goal cell: drafted, then edited (the veto surface)
# --------------------------------------------------------------------------- #
def test_accept_stores_the_literal_gate_without_a_model(env):
    rec = launch.accept("what is the median fleet latency?", enqueue=False)
    assert rec["gate"]["kind"] == "shell_ok"
    assert rec["goal_state"] == launch.GOAL_PENDING
    repo = launch.accept("implement the retry path and open a PR", enqueue=False)
    assert repo["gate"]["kind"] == "pr_open"
    compute = launch.accept("run the sweep into results.jsonl and open a PR",
                            enqueue=False)
    assert compute["gate"]["kind"] == "pr_open_and_shell_ok"
    assert compute["gate"]["arg"] == "test -s results.jsonl"


def test_router_drafts_the_goal_onto_the_record(env):
    env.add_stub("known-thread")
    rec = launch.accept("summarize this week's eval runs", dry_run=True,
                        enqueue=False)
    runner = lambda *_a, **_k: {"text": json.dumps({
        "slug": "known-thread", "reading": "r", "assumptions": "a",
        "deliverables": "a markdown digest at report.md",
        "exit_criteria": "report.md is non-empty"})}
    out = launch.process_intent(rec["id"], runner=runner)
    assert out["goal_state"] == launch.GOAL_DRAFTED
    assert "markdown digest" in out["goal"] and "non-empty" in out["goal"]
    # and the interpretation note carries it too (row detail click-through)
    bodies = "\n".join(n["body"] for n in note.load_notes("known-thread"))
    assert "markdown digest" in bodies


def test_offline_router_still_populates_a_goal(env):
    rec = launch.accept("what broke the nightly sweep?", slug="q", dry_run=True,
                        enqueue=False)
    out = launch.process_intent(rec["id"], runner=_offline)
    assert out["goal"].startswith("Deliverables:")
    assert ".threads-result.md" in out["goal"]


def test_goal_edit_pre_spawn_changes_the_gate_the_executor_receives(env,
                                                                   monkeypatch):
    """DoD 3, end to end: edit the Goal before spawn, and the gate object handed
    to the concierge pool is the re-derived one."""
    pytest.importorskip("concierge",
                        reason="concierge retired to jarvis-tools/attic/ "
                               "(2026-09-16 sweep); test revives with it")
    rec = launch.accept("what is the median fleet latency?", slug="pre",
                        enqueue=False)
    assert launch.gate_spec_for(launch.load_intent(rec["id"]))["kind"] == "shell_ok"
    launch.set_goal(rec["id"], "Deliverables: a PR adding the latency probe.\n\n"
                               "Done when: an open PR exists on the launch branch.")
    edited = launch.load_intent(rec["id"])
    assert edited["goal_state"] == launch.GOAL_EDITED
    assert launch.gate_spec_for(edited)["kind"] == "pr_open"

    captured = {}

    class FakePool:
        def __init__(self, home=None):
            pass

        def submit(self, spec, **kw):
            captured.update(spec=spec, **kw)
            return "t-submitted"

    import concierge.api
    monkeypatch.setattr(concierge.api, "Pool", FakePool)
    monkeypatch.setenv("THREADS_LAUNCH_REPO", str(env.root))
    handle = launch._full_auto(edited, "pre", "interpretation")
    assert handle == "t-submitted"
    assert type(captured["gate"]).__name__ == "PrOpen"     # not ShellOk
    assert "latency probe" in captured["spec"]             # goal is in the seed


def test_goal_edit_pre_spawn_survives_async_routing(env):
    rec = launch.accept("what is the median fleet latency?", slug="pre2",
                        dry_run=True, enqueue=False)
    launch.set_goal(rec["id"], "Deliverables: open a PR with the probe.")
    routed = launch.process_intent(rec["id"], runner=_offline)
    assert routed["goal_state"] == launch.GOAL_EDITED
    assert "open a PR with the probe" in routed["goal"]
    assert launch.gate_spec_for(routed)["kind"] == "pr_open"


def test_goal_edit_post_spawn_lands_as_pool_msg_and_flags_the_row(env):
    pytest.importorskip("concierge",
                        reason="concierge retired to jarvis-tools/attic/ "
                               "(2026-09-16 sweep); test revives with it")
    env.add_task("t-live", title="thread launch: post")
    _task(env, "t-live", status="running")
    rec = _intent("implement the parser", slug="post", tid="t-live")
    out = launch.set_goal(rec["id"], "Deliverables: the parser plus a "
                                     "regression test.")
    assert out["goal_flagged"] is True
    assert out.get("goal_msg_error") is None
    mailbox = (env.concierge / "mailbox" / "t-live.jsonl").read_text()
    assert "regression test" in mailbox
    row = board.launched_row(out, now=NOW, cfg=config.Config(), notes_by_slug={})
    assert row.goal_flagged
    assert "edited after spawn" in board._goal_cell(row)


def test_goal_edit_after_the_gate_passed_does_not_re_derive_it(env):
    _task(env, "t-settled", status="done", gate_passed=True)
    rec = _intent("write the answer", slug="settled", tid="t-settled",
                  state="terminal", terminal="result")
    before = launch.gate_spec_for(rec)["kind"]
    out = launch.set_goal(rec["id"], "Deliverables: open a PR instead.")
    assert launch.gate_spec_for(out)["kind"] == before
    assert out["goal_flagged"] is True      # still visible as a discrepancy


def test_goal_edit_without_a_mailbox_flags_the_row_instead_of_failing(env):
    rec = _intent("pair with me", slug="cop", tid="thread-cop-x", mode="copilot")
    out = launch.set_goal(rec["id"], "Deliverables: the parser.")
    assert out["goal_flagged"] and "no concierge mailbox" in out["goal_msg_error"]


def test_goal_edit_records_history_and_rejects_empty(env):
    rec = launch.accept("do a thing", slug="hist", enqueue=False)
    launch.set_goal(rec["id"], "first goal")
    launch.set_goal(rec["id"], "second goal")
    saved = launch.load_intent(rec["id"])
    assert [h["text"] for h in saved["goal_history"]] == ["first goal",
                                                          "second goal"]
    assert saved["goal_history"][1]["previous"] == "first goal"
    assert all(h["phase"] == "pre-spawn" for h in saved["goal_history"])
    with pytest.raises(ValueError):
        launch.set_goal(rec["id"], "   ")


@pytest.mark.parametrize("text", [
    "what is the median latency of the fleet?",
    "implement the retry path and open a PR",
    "run the sweep into results.jsonl and open a PR",
])
def test_drafted_goal_is_gate_derivation_stable(text):
    spec = launch.gate_spec(None, text)
    again = launch.gate_spec(launch.fallback_goal(text, spec), text)
    assert again == spec


def test_gate_spec_builds_the_concierge_gate_object():
    spec = launch.gate_spec(None, "implement the parser and open a PR")
    assert "PrOpen" in spec["name"]
    assert type(launch.gate_object(spec)).__name__ == "PrOpen"
    compound = launch.gate_spec(None, "sweep into results.jsonl and open a PR")
    assert type(launch.gate_object(compound)).__name__ not in ("PrOpen", "ShellOk")


def test_pr_matches_as_a_word_not_a_prefix():
    """"improve"/"approach" must not read as "open a PR" (they used to)."""
    assert launch.gate_spec(None, "improve the wording of the goals README"
                            )["kind"] == "shell_ok"
    assert launch.gate_spec(None, "what approach should we take to evals?"
                            )["kind"] == "shell_ok"
    assert launch.gate_spec(None, "open a PR for the docs")["kind"] == "pr_open"
    assert launch.gate_spec(None, "why did the sweep skip two PRs?"
                            )["kind"] == "pr_open"   # PRs is the subject: veto
                                                     # via the Goal cell if wrong


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def test_board_renders_three_columns_add_box_and_is_responsive(env):
    _task(env, "t-r", status="running")
    _intent("do the thing", slug="render-me", tid="t-r")
    page = board.render_html(board.build(now=NOW, sweep=False))
    assert "<th>Prompt</th><th>Goal</th><th>Status</th>" in page
    assert "add-text" in page and "addRow" in page      # top-of-table row add
    assert "width=device-width" in page                  # phone-usable
    assert "@media(max-width:52rem)" in page
    assert "do the thing" in page


def test_row_detail_shows_notes_interpretation_and_handles(env):
    _task(env, "t-d", status="running")
    rec = _intent("do the thing", slug="detail-me", tid="t-d")
    note.add_note("detail-me", "Reading + assumptions:\n\nbecause X",
                  title="router interpretation", now=NOW)
    note.add_note("detail-me", "parked mid-stream", status="parked", now=NOW)
    row = board.launched_row(rec, now=NOW, cfg=config.Config(),
                             notes_by_slug={"detail-me": note.load_notes("detail-me")})
    cell = board._prompt_cell(row)
    assert "because X" in cell                      # interpretation
    assert "parked mid-stream" in cell or "parked" in cell
    assert "t-d" in cell                            # executor handle
    assert "detach" in cell and "merge into thread" in cell


def test_page_load_makes_no_model_call(env, monkeypatch):
    _intent("no model please", slug="cheap", tid=None, state="routed")

    def boom(*_a, **_k):
        raise AssertionError("a page load must never call a model")

    monkeypatch.setattr(summarize, "default_runner", boom)
    page = board.render_html(board.build(now=NOW, sweep=False))
    assert "no model please" in page


def test_text_rendering_lists_rows_in_board_order(env):
    _task(env, "t-t", status="blocked", detail="which bucket?")
    _intent("blocked work", slug="t-text", tid="t-t")
    text = board.render_text(board.build(now=NOW, sweep=False))
    assert "blocked work" in text and "which bucket?" in text
    assert text.splitlines()[0].startswith("thread board —")


# --------------------------------------------------------------------------- #
# candidate delete
# --------------------------------------------------------------------------- #
def test_delete_candidate_removes_only_that_file(env):
    config.ensure_spool()
    (config.candidates_dir() / "cand-a.md").write_text("# a\n- s1\n")
    (config.candidates_dir() / "cand-b.md").write_text("# b\n- s2\n")
    assert board.delete_candidate("cand-a") == {"slug": "cand-a", "deleted": True}
    assert not (config.candidates_dir() / "cand-a.md").exists()
    assert (config.candidates_dir() / "cand-b.md").exists()
    assert board.delete_candidate("cand-a")["deleted"] is False   # idempotent
    for bad in ("../etc/passwd", "a/b", "", "a.md"):
        with pytest.raises(ValueError):
            board.delete_candidate(bad)


# --------------------------------------------------------------------------- #
# serving: the board is the default page
# --------------------------------------------------------------------------- #
def _get(srv, path):
    port = int(srv.local_url.rsplit(":", 1)[1])
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, resp.read().decode()


def _post(srv, path, body):
    port = int(srv.local_url.rsplit(":", 1)[1])
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("POST", path, body=json.dumps(body),
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    return resp.status, resp.read().decode()


def test_board_is_the_default_page_dashboard_is_secondary(env):
    _intent("served row", slug="serve-me", tid=None, state="routed")
    srv = server.serve(tunnel=False, interval=3600)
    try:
        status, page = _get(srv, "/")
        assert status == 200
        assert "<h1>thread board</h1>" in page and "served row" in page
        status, dash_page = _get(srv, "/dashboard")
        assert status == 200
        assert "threads — activity dashboard" in dash_page
        assert "thread board" in dash_page          # links back
    finally:
        srv.stop()


def test_row_add_is_visible_on_the_next_render(env):
    srv = server.serve(tunnel=False, interval=3600)
    try:
        status, body = _post(srv, "/launch", {"text": "brand new intent"})
        assert status == 202
        assert json.loads(body)["gate"]["kind"]
        status, page = _get(srv, "/")
        assert "brand new intent" in page
    finally:
        srv.stop()


def test_goal_endpoint_edits_the_cell(env):
    rec = launch.accept("edit me", slug="ep", enqueue=False)
    srv = server.serve(tunnel=False, interval=3600)
    try:
        status, body = _post(srv, "/goal",
                             {"id": rec["id"], "goal": "Deliverables: a PR."})
        assert status == 200
        assert json.loads(body)["goal_state"] == launch.GOAL_EDITED
        assert launch.gate_spec_for(launch.load_intent(rec["id"]))["kind"] == "pr_open"
        status, _ = _post(srv, "/goal", {"id": rec["id"], "goal": ""})
        assert status == 400
    finally:
        srv.stop()


def test_candidate_delete_and_tail_endpoints(env):
    config.ensure_spool()
    (config.candidates_dir() / "cand-x.md").write_text("# x\n- s\n")
    (env.concierge / "logs" / "t-tail" / "attempt-1").mkdir(parents=True)
    (env.concierge / "logs" / "t-tail" / "attempt-1" / "agent.jsonl").write_text(
        "hello from the log\n")
    srv = server.serve(tunnel=False, interval=3600)
    try:
        status, _ = _post(srv, "/candidate-delete", {"slug": "cand-x"})
        assert status == 200
        assert not (config.candidates_dir() / "cand-x.md").exists()
        status, page = _get(srv, "/tail?tid=t-tail")
        assert status == 200 and "hello from the log" in page
    finally:
        srv.stop()


def test_disable_enqueue_env_is_honoured(env, monkeypatch):
    """The seam board --check uses to exercise POST /launch without spawning."""
    seen = []
    monkeypatch.setattr(launch.subprocess, "Popen",
                        lambda *a, **k: seen.append(a))
    monkeypatch.setenv("THREADS_DISABLE_ENQUEUE", "1")
    _REAL_ENQUEUE("01ABC")
    assert seen == []
    monkeypatch.delenv("THREADS_DISABLE_ENQUEUE")
    _REAL_ENQUEUE("01ABC")
    assert len(seen) == 1


# --------------------------------------------------------------------------- #
# the gate itself
# --------------------------------------------------------------------------- #
def _snapshot(root):
    return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size)
                  for p in root.rglob("*") if p.is_file())


def test_board_check_passes_and_leaves_the_spool_untouched(env, capsys):
    """--check is a *read* of the live spool: every write-shaped assertion runs
    against a fixture spool in a temp dir."""
    config.ensure_spool()
    _task(env, "t-real", status="running")
    _intent("a real row", slug="real-thread", tid="t-real")
    note.add_note("some-thread", "context", status="parked", now=NOW)
    before = _snapshot(config.threads_dir())
    ok, report = board.board_check()
    assert ok, report
    assert "board --check OK" in report
    assert _snapshot(config.threads_dir()) == before
    # the gate reports what it verified, not just a verdict
    for claim in ("zero model calls on page load",
                  "pre-spawn goal edit re-derives the gate",
                  "post-spawn edit is delivered to the worker as pool.msg",
                  "violations then blocked pin to the top",
                  "the board is the default page at the threads URL",
                  "worker result_text never reaches the Status cell",
                  "row add is durable in <100ms"):
        assert claim in report


def test_board_check_fails_when_status_derivation_regresses(env, monkeypatch):
    """The gate is only worth having if it can fail: break the pool→lifecycle
    mapping and it must notice."""
    monkeypatch.setitem(board.POOL_LIFECYCLE, "blocked", "running")
    ok, report = board.board_check()
    assert not ok
    assert "FAIL" in report


def test_cli_board_and_check(env, capsys):
    _intent("cli row", slug="cli-thread", tid=None, state="routed")
    assert main(["board"]) == 0
    out = capsys.readouterr().out
    assert "cli row" in out
    assert main(["board", "--check"]) == 0
    assert "board --check OK" in capsys.readouterr().out
    assert main(["board", "--html"]) == 0
    assert "<h1>thread board</h1>" in capsys.readouterr().out


def test_existing_verbs_stay_green(env, canned_runner, capsys):
    """The board must not disturb the rest of the CLI (launch --check included)."""
    assert main(["launch", "--check"]) == 0
    assert "launch --check OK" in capsys.readouterr().out
    assert main(["render"]) == 0
    assert main(["status"]) in (0, 1)   # status prints check verdicts, never raises
