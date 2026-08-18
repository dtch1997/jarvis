"""route: triage batching, per-type actuation, the file-never-complete rule,
move/close split, reply_on_route, and route_check."""

from __future__ import annotations

from mailroom import config, ingest, route, spool, todoist

from mailroom_testkit import CH, NOW, FakeSlack, FakeTodoist, slack_msg


def _todoist_task(tid, content):
    return {"id": tid, "content": content, "project_id": config.TODOIST_INBOX_ID,
            "created_at": "2026-08-15T00:00:00Z", "labels": []}


def _ingest(slack, td, *, backfill=True, transcriber=None):
    return ingest.ingest(backfill=backfill, client=slack, todoist_client=td,
                         transcriber=transcriber or (lambda w: "x"), now=NOW)


def test_triage_batches_and_writes(env, triage_runner, note_calls):
    slack = FakeSlack([slack_msg("100", text="note: the widget work"),
                       slack_msg("101", text="buy a todo item")])
    td = FakeTodoist()
    _ingest(slack, td)
    res = route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                      note_runner=note_calls, now=NOW)
    assert res.triaged == 2
    assert res.model_calls == 1  # both fit in one batch
    rec = spool.load_thought(f"slack-{CH}-100")
    assert rec["triage"]["type"] == "thread-note"
    assert rec["route"]["action"] == "threads-note"


def test_slack_todo_creates_task_not_move(env, triage_runner, note_calls):
    slack = FakeSlack([slack_msg("100", text="todo: ship it")])
    td = FakeTodoist()
    _ingest(slack, td)
    route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                note_runner=note_calls, now=NOW)
    assert ("create", config.TODOIST_PROJECTS["Focus Areas"], "todo: ship it"[:40]) in \
        [(op, pid, arg[:40]) for (op, pid, arg) in td.log if op == "create"]


def test_todoist_todo_is_moved_never_completed(env, triage_runner, note_calls):
    # a task-typed Inbox item MUST be moved (stays open), never closed.
    slack = FakeSlack([])
    td = FakeTodoist(inbox=[_todoist_task("t1", "buy milk todo")])
    _ingest(slack, td)
    res = route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                      note_runner=note_calls, now=NOW)
    ops = [op for (op, _, _) in td.log]
    assert "move" in ops
    assert "close" not in ops              # never completed
    assert res.task_completions == 0
    assert res.todoist_moved == 1
    rec = spool.load_thought("todoist-t1")
    assert rec["route"]["action"] == "todoist-move"


def test_todoist_nontask_is_closed_with_transfer(env, triage_runner, note_calls):
    # a research-idea in the Inbox → seeded as a thread note, original CLOSED
    # with a transfer comment (custody transfer, not completion).
    slack = FakeSlack([])
    td = FakeTodoist(inbox=[_todoist_task("t1", "idea: a cool research idea")])
    _ingest(slack, td)
    res = route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                      note_runner=note_calls, now=NOW)
    ops = [op for (op, _, _) in td.log]
    assert "close" in ops
    assert "comment" in ops
    assert res.todoist_closed == 1
    assert res.task_completions == 0       # a non-task close is not a completion
    assert note_calls.calls  # landed as a note


def test_goal_signal_appends_bullet(env, triage_runner, note_calls):
    env.add_goal("phd-thesis")
    slack = FakeSlack([slack_msg("100", text="goal: prioritize the thesis chapter")])
    _ingest(slack, FakeTodoist())
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=slack, note_runner=note_calls,
                goals_dir=env.goals, now=NOW)
    text = (env.goals / "phd-thesis.md").read_text()
    assert "via mailroom" in text
    assert "Parked follow-ups" in text


def test_paper_creates_papers_task(env, triage_runner, note_calls):
    calls = []
    slack = FakeSlack([slack_msg("100", text="paper: read this important paper")])
    td = FakeTodoist()
    _ingest(slack, td)
    route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                note_runner=note_calls, arxiv_runner=lambda x: calls.append(x) or True,
                now=NOW)
    assert any(op == "create" and pid == config.TODOIST_PROJECTS["Papers to read"]
               for (op, pid, _) in td.log)
    assert calls == ["2401.00001"]  # arxivist fetched


def test_unclear_slack_stays_at_source(env, triage_runner, note_calls):
    slack = FakeSlack([slack_msg("100", text="mmm hmm")])
    _ingest(slack, FakeTodoist())
    res = route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                      slack_client=slack, note_runner=note_calls, now=NOW)
    rec = spool.load_thought(f"slack-{CH}-100")
    assert rec["route"]["action"] == "unclear"
    assert res.unclear == 1


def test_unclear_todoist_gets_labeled(env, triage_runner, note_calls):
    td = FakeTodoist(inbox=[_todoist_task("t1", "mmm hmm")])
    _ingest(FakeSlack([]), td)
    route.route(runner=triage_runner, todoist_client=td, slack_client=FakeSlack([]),
                note_runner=note_calls, now=NOW)
    assert ("label", "t1", "mailroom-unclear") in td.log
    assert spool.load_thought("todoist-t1")["route"]["action"] == "label-unclear"


def test_reply_on_route_only_incremental(env, triage_runner, note_calls):
    # backfill message: no reply. incremental message: reply.
    slack = FakeSlack([slack_msg("100", text="note: backfilled work")])
    _ingest(slack, FakeTodoist(), backfill=True)
    slack.messages.append(slack_msg("200", text="note: fresh work"))
    _ingest(slack, FakeTodoist(), backfill=False)
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=slack, note_runner=note_calls, now=NOW)
    replied_ts = [ts for (_, ts, _) in slack.posts]
    assert "200" in replied_ts
    assert "100" not in replied_ts


def test_route_idempotent(env, triage_runner, note_calls):
    slack = FakeSlack([slack_msg("100", text="note: a thing")])
    _ingest(slack, FakeTodoist())
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=slack, note_runner=note_calls, now=NOW)
    n_notes = len(note_calls.calls)
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=slack, note_runner=note_calls, now=NOW)
    assert len(note_calls.calls) == n_notes  # no re-actuation
    assert triage_runner.calls["n"] == 1     # no re-triage


def test_route_check_thresholds(env, triage_runner, note_calls):
    msgs = [slack_msg(str(100 + i), text="note: work item") for i in range(9)]
    msgs.append(slack_msg("200", text="mmm"))  # 1 unclear of 10 → 90% routed
    _ingest(FakeSlack(msgs), FakeTodoist())
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=FakeSlack(msgs), note_runner=note_calls, now=NOW)
    ok, report = route.route_check(now=NOW)
    assert ok, report
    assert "0 task-completions" in report


def test_route_check_fails_below_threshold(env, triage_runner, note_calls):
    msgs = [slack_msg(str(100 + i), text="mmm") for i in range(9)]  # all unclear
    msgs.append(slack_msg("200", text="note: one routed"))
    _ingest(FakeSlack(msgs), FakeTodoist())
    route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                slack_client=FakeSlack(msgs), note_runner=note_calls, now=NOW)
    ok, report = route.route_check(now=NOW)
    assert not ok
    assert "<" in report


def test_urgent_captures_batch_into_one_flare(env, triage_runner, note_calls,
                                              monkeypatch):
    # two fresh urgent Todoist captures → exactly ONE warn flare naming both;
    # per-item flares flooded the channel (2026-08-17).
    from mailroom import actuators
    flares = []
    monkeypatch.setattr(actuators, "send_flare",
                        lambda msg, **kw: flares.append((msg, kw)) or True)
    slack = FakeSlack([])
    td = FakeTodoist(inbox=[_todoist_task("t1", "urgent: visa deadline"),
                            _todoist_task("t2", "urgent: server on fire")])
    _ingest(slack, td)
    res = route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                      note_runner=note_calls, now=NOW)
    assert len(res.urgent) == 2
    assert len(flares) == 1
    msg, kw = flares[0]
    assert msg.splitlines()[0] == "mailroom: 2 urgent captures"
    # one bullet per point (Daniel's readability preference)
    assert "• urgent: visa deadline" in msg
    assert "• urgent: server on fire" in msg
    assert kw.get("sev", "warn") == "warn"
    assert "1 urgent" not in res.report() and "2 urgent" in res.report()


def test_stale_urgent_capture_never_flares(env, triage_runner, note_calls,
                                           monkeypatch):
    # triage says "high" but the thought is weeks old (slack test ts ≈ 1970) —
    # stale items can't be time-sensitive, so no flare at all.
    from mailroom import actuators
    flares = []
    monkeypatch.setattr(actuators, "send_flare",
                        lambda msg, **kw: flares.append(msg) or True)
    slack = FakeSlack([slack_msg("100", text="urgent old thing")])
    td = FakeTodoist()
    _ingest(slack, td)
    res = route.route(runner=triage_runner, todoist_client=td, slack_client=slack,
                      note_runner=note_calls, now=NOW)
    assert res.urgent == []
    assert flares == []
