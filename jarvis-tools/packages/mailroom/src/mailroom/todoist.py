from __future__ import annotations
import os
from .http import request
API="https://api.todoist.com/api/v1"
def _token(): return os.environ["TODOIST_API_TOKEN"]
def pages(path, params=None):
    out=[]; cursor=None
    while True:
        p=dict(params or {})
        if cursor:p["cursor"]=cursor
        r=request(API+path,token=_token(),params=p); out += r.get("results",r if isinstance(r,list) else [])
        cursor=r.get("next_cursor") if isinstance(r,dict) else None
        if not cursor: return out
def inbox(project_id): return pages("/tasks", {"project_id":project_id})
def projects(): return pages("/projects")
def all_open(): return pages("/tasks")
def stale_candidates(inbox_id, days):
    """Propose-only: curated-project (non-Inbox) tasks whose added_at predates
    the window. mailroom never closes these — the digest just lists them."""
    import datetime as _dt
    cutoff=(_dt.datetime.now(_dt.timezone.utc)-_dt.timedelta(days=days)).isoformat()
    out=[]
    for t in all_open():
        if t.get("project_id")==inbox_id: continue
        added=t.get("added_at") or ""
        if added and added<cutoff: out.append({"id":t["id"],"content":t.get("content",""),"project_id":t.get("project_id"),"added_at":added})
    return out
def comment(task_id,text): return request(API+"/comments",token=_token(),method="POST",data={"task_id":task_id,"content":text})
def move(task_id,project_id): return request(API+f"/tasks/{task_id}/move",token=_token(),method="POST",data={"project_id":project_id})
def close(task_id): return request(API+f"/tasks/{task_id}/close",token=_token(),method="POST",data={})
def label_unclear(task):
    labels=list(task.get("labels") or [])
    if "mailroom-unclear" not in labels: labels.append("mailroom-unclear")
    return request(API+f"/tasks/{task['id']}",token=_token(),method="POST",data={"labels":labels})
