from __future__ import annotations
import datetime as dt, os, subprocess
from pathlib import Path
from . import config, spool, todoist, triage

def _goals_dir():
    # goals live at <root>/jarvis-os/goals in the monorepo and <jarvis>/goals in
    # the deployed split-repo layout — resolve by search so both work, with an
    # explicit MAILROOM_GOALS_DIR override for anything unusual.
    import os
    if os.environ.get("MAILROOM_GOALS_DIR"): return Path(os.environ["MAILROOM_GOALS_DIR"])
    here=Path(__file__).resolve()
    for base in here.parents:
        for cand in (base/"jarvis-os"/"goals", base/"goals"):
            if (cand/"README.md").exists() and (cand/"TEMPLATE.md").exists(): return cand
    return Path.home()/"jarvis"/"goals"
def _slugs():
    p=Path.home()/"jarvis-memory"/"MEMORY.md"
    return [] if not p.exists() else [x.name for x in (Path.home()/"jarvis-memory").glob("*.md") if x.name!="MEMORY.md"]
def _goals():
    d=_goals_dir()
    return [p.name for p in d.glob("*.md") if p.name not in {"README.md","TEMPLATE.md"}] if d.exists() else []
def _project_map(): return {p["name"]:p["id"] for p in todoist.projects()}
def _pick_project(name, projects):
    # Return a concrete non-Inbox project id, or None when triage gave no
    # confident placement — callers treat None as "leave in Inbox, unclear"
    # rather than fake-moving into an arbitrary project (there is no generic
    # Personal/Work catch-all in Daniel's board).
    if not name: return None
    if name in projects and name != "Inbox": return projects[name]
    lower=name.lower()
    for n,i in projects.items():
        if n!="Inbox" and (lower in n.lower() or n.lower() in lower): return i
    return None
def _thread_note(slug,title,raw):
    slug=slug or "mailroom-captures"
    subprocess.run(["threads","note",slug,"-"],input=f"## {title}\n\n{raw}\n",text=True,check=True)
    return f"threads:{slug}"
def _goal_bullet(goal,title,raw):
    names=_goals()
    if not names: raise RuntimeError("no goal files found")
    goal=goal if goal in names else ("self-driving-jarvis.md" if "self-driving-jarvis.md" in names else names[0])
    p=_goals_dir()/goal
    stamp=dt.date.today().isoformat(); marker="## Parked follow-ups"
    text=p.read_text(); bullet=f"\n- {stamp} — {title}: {raw.strip()} (via mailroom)\n"
    if marker in text: text=text.replace(marker,marker+bullet,1)
    else: text+=f"\n{marker}{bullet}"
    p.write_text(text); return f"goal:{goal}"

def route(max_calls=None):
    state=spool.load_state(); records=[r for r in spool.load_all() if not r.get("route")]; cfg=config.load()
    cap=cfg.max_model_calls if max_calls is None else max_calls
    projects=_project_map(); calls=0; cost=0.0; truncated=False
    if records and cap>0:
        assignments,cost,calls,truncated=triage.run(records,sorted(projects),_slugs(),_goals(),cap)
        if truncated:
            subprocess.run(["flare",f"mailroom: triage cap ({cap} calls) hit — {len(records)} records pending, some unrouted","--sev","warn"],check=False)
    else: assignments={}
    stats={"moved":0,"closed_non_task":0,"task_completions":0,"created":0,"unclear":0,"actions":{}}
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    for r in records:
        t=assignments.get(r["id"],{"type":"unclear","title":r["raw"][:80],"candidate_slugs":[],"goal":None,"urgency":"low","target_project":None}); r["triage"]=t
        typ=t["type"]; target=""; action="unclear"
        try:
            from .http import request
            if typ in {"todo","admin"}:
                pid=_pick_project(t.get("target_project"),projects)
                if pid is None:
                    typ="unclear"  # can't place confidently → keep open, label, digest
                elif r["source"]=="todoist":
                    # File, NEVER complete: move keeps the task open in a curated project.
                    todoist.comment(r["source_meta"]["task_id"],"mailroom: filed from Inbox"); todoist.move(r["source_meta"]["task_id"],pid); stats["moved"]+=1; action="todoist-move"; target=t.get("target_project")
                else:
                    task=request("https://api.todoist.com/api/v1/tasks",token=os.environ["TODOIST_API_TOKEN"],method="POST",data={"content":t["title"],"description":r["raw"]+"\n\nsource: "+r.get("source_permalink",r["permalink"]),"project_id":pid}); target=task.get("id",""); stats["created"]+=1; action="todoist-create"
            if typ in {"thread-note","research-idea"}:
                target=_thread_note((t.get("candidate_slugs") or [None])[0],t["title"],r["raw"]); action="threads-note"
            elif typ=="goal-signal": target=_goal_bullet(t.get("goal"),t["title"],r["raw"]); action="goal-bullet"
            elif typ=="paper":
                pid=_pick_project("Papers to read",projects)
                task=request("https://api.todoist.com/api/v1/tasks",token=os.environ["TODOIST_API_TOKEN"],method="POST",data={"content":t["title"],"description":r["raw"],"project_id":pid}); target=task.get("id",""); action="paper-task"; stats["created"]+=1
            elif typ=="unclear":
                if r["source"]=="todoist": todoist.label_unclear({"id":r["source_meta"]["task_id"],"labels":r["source_meta"].get("labels",[])})
                stats["unclear"]+=1
            # Inbox non-task captures close only after successful custody transfer.
            if r["source"]=="todoist" and typ in {"thread-note","research-idea","goal-signal","paper"} and action!="unclear":
                tid=r["source_meta"]["task_id"]; todoist.comment(tid,f"mailroom: custody transferred to {target or action}"); todoist.close(tid); stats["closed_non_task"]+=1
            r["route"]={"action":action,"target":target or t.get("target_project") or "","at":now}; spool.write(r); stats["actions"][action]=stats["actions"].get(action,0)+1
            if r["source"] in {"slack","voice"} and not r.get("source_meta",{}).get("backfill") and action!="unclear" and cfg.reply_on_route:
                from .slack import reply
                meta=r["source_meta"]; reply(meta["channel"],meta.get("thread_ts") or meta["message_ts"],f"mailroom: routed via {action} → {target or t.get('target_project') or 'filed'}")
        except Exception as e:
            r["route_error"]=str(e); spool.write(r)
    remaining=len(todoist.inbox(config.TODOIST_INBOX_ID))
    baseline=state.get("todoist_baseline",remaining)
    total=len(spool.load_all()); routed=sum(bool(r.get("route")) and r["route"].get("action")!="unclear" for r in spool.load_all())
    state["last_route"]={"at":now,"stats":stats,"model_calls":calls,"model_spend_usd":cost,"todoist_drain":{"before":baseline,"after":remaining},"routed":routed,"total":total,"auto_route_rate":routed/total if total else 0}
    spool.write_state(state); return state["last_route"]

def check():
    s=spool.load_state().get("last_route",{}); stats=s.get("stats",{}); rate=s.get("auto_route_rate",0)
    ok=rate>=.8 and "todoist_drain" in s and stats.get("task_completions")==0 and s.get("routed",0)>0
    return ok,f"route check: {'OK' if ok else 'FAIL'}; routed={s.get('routed',0)}/{s.get('total',0)} ({rate:.1%}); drain={s.get('todoist_drain')}; task completions={stats.get('task_completions')}"
