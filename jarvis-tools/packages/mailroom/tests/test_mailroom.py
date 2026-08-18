from __future__ import annotations
import json

def test_spool_roundtrip(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom import spool
    spool.write({"id":"slack:C:1.0","source":"slack","raw":"hello"})
    assert spool.ids()=={"slack:C:1.0"}
    assert spool.load_all()[0]["raw"]=="hello"

def test_gate_checks_are_offline(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom import spool
    records=[{"id":f"slack:C:{i}","source":"slack","route":{"action":"threads-note"}} for i in range(4)]
    for r in records:spool.write(r)
    spool.write_state({"slack_backfill_complete":True,"last_ingest":{"new":0,"elapsed_seconds":.2,"model_calls":0,"discovered":{"slack":4,"todoist":0},"errors":[]},"last_route":{"routed":4,"total":4,"auto_route_rate":1.0,"todoist_drain":{"before":2,"after":0},"stats":{"task_completions":0}}})
    from mailroom.ingest import check as ingest_check
    from mailroom.route import check as route_check
    assert ingest_check()[0]
    assert route_check()[0]

def test_route_check_fails_on_task_completion(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom import spool
    spool.write({"id":"x","source":"todoist","route":{"action":"todoist-move"}})
    spool.write_state({"last_route":{"routed":1,"total":1,"auto_route_rate":1.0,"todoist_drain":{"before":1,"after":0},"stats":{"task_completions":1}}})
    from mailroom.route import check
    assert not check()[0]  # any task completion fails the gate

def test_route_check_fails_below_80pct(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom import spool
    spool.write_state({"last_route":{"routed":7,"total":10,"auto_route_rate":0.7,"todoist_drain":{"before":1,"after":0},"stats":{"task_completions":0}}})
    from mailroom.route import check
    assert not check()[0]

def test_todoist_pagination(monkeypatch):
    from mailroom import todoist
    calls=[]
    def fake(url,**kw):
        calls.append(kw.get("params",{}));return {"results":[{"id":len(calls)}],"next_cursor":"n" if len(calls)==1 else None}
    monkeypatch.setattr(todoist,"request",fake)
    assert len(todoist.pages("/tasks"))==2
    assert calls[1]["cursor"]=="n"

def test_todoist_move_uses_move_endpoint(monkeypatch):
    from mailroom import todoist
    seen={}
    def fake(url,**kw):
        seen["url"]=url;seen["data"]=kw.get("data");return {}
    monkeypatch.setattr(todoist,"request",fake)
    monkeypatch.setenv("TODOIST_API_TOKEN","x")
    todoist.move("T1","P2")
    assert seen["url"].endswith("/tasks/T1/move")  # v1 needs the dedicated move endpoint
    assert seen["data"]=={"project_id":"P2"}

def test_slack_form_encoding_lowercases_bools():
    import urllib.request
    from mailroom import http
    captured={}
    class FakeResp:
        def read(self): return b'{"ok":true}'
        def __enter__(self): return self
        def __exit__(self,*a): return False
    def fake_urlopen(req,timeout=0):
        captured["body"]=req.data; captured["ct"]=req.headers.get("Content-type"); return FakeResp()
    orig=urllib.request.urlopen; urllib.request.urlopen=fake_urlopen
    try:
        http.request("https://slack/api/x",token="t",method="POST",data={"inclusive":True,"drop":None,"n":5},slack=True)
    finally:
        urllib.request.urlopen=orig
    assert b"inclusive=true" in captured["body"]  # not "True"
    assert b"drop" not in captured["body"]         # None dropped
    assert "x-www-form-urlencoded" in captured["ct"]

def test_pick_project_returns_none_without_match():
    from mailroom.route import _pick_project
    projects={"Inbox":"i","PhD":"p","Tools":"t"}
    assert _pick_project("PhD",projects)=="p"
    assert _pick_project("Inbox",projects) is None      # never fake-move to Inbox
    assert _pick_project("nonexistent",projects) is None
    assert _pick_project(None,projects) is None

def test_transcribe_missing_venv_raises(monkeypatch,tmp_path):
    from mailroom import transcribe
    monkeypatch.setenv("MAILROOM_ASR_PYTHON",str(tmp_path/"nope"/"python"))
    try:
        transcribe.transcribe(tmp_path/"a.wav"); assert False
    except RuntimeError as e:
        assert "ASR venv" in str(e)

def test_cli_check_exit_codes(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom.cli import main
    assert main(["ingest","--check"])==1
    assert main(["route","--check"])==1

def test_render(tmp_path,monkeypatch):
    monkeypatch.setenv("MAILROOM_HOME",str(tmp_path))
    from mailroom import spool
    spool.write({"id":"x","source":"todoist","raw":"capture"})
    from mailroom.dashboard import render_markdown
    out=render_markdown()
    assert "mailroom digest" in out
    assert "task-completions 0" in out
