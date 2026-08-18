from __future__ import annotations
import html
from . import config, spool

def _stale_lines():
    # Best-effort, propose-only. Never fails render (offline gates, missing token).
    try:
        from . import todoist
        cfg=config.load(); cand=todoist.stale_candidates(config.TODOIST_INBOX_ID, cfg.stale_days)
        if not cand: return ["_none_"]
        return [f"- `{c['id']}` {c['content'][:80]} (added {c['added_at'][:10]})" for c in cand[:50]]
    except Exception as e:
        return [f"_stale sweep skipped: {e}_"]

def render_markdown(*, stale=False):
    records=spool.load_all(); state=spool.load_state()
    li=state.get("last_ingest",{}); lr=state.get("last_route",{}); stats=lr.get("stats",{})
    by_type={}
    for r in records:
        ty=r.get("triage",{}).get("type","pending"); by_type[ty]=by_type.get(ty,0)+1
    drain=lr.get("todoist_drain",{})
    lines=["# mailroom digest","",
        f"- Thoughts retained: **{len(records)}** ({li.get('counts',{})})",
        f"- Auto-route rate: **{lr.get('auto_route_rate',0):.1%}** ({lr.get('routed',0)}/{lr.get('total',0)})",
        f"- Todoist drain: **{drain.get('before','?')} → {drain.get('after','?')}** (moved {stats.get('moved',0)}, closed-non-task {stats.get('closed_non_task',0)}, created {stats.get('created',0)}, **task-completions {stats.get('task_completions',0)}**)",
        f"- Model spend (last route): **${lr.get('model_spend_usd',0):.4f}** in {lr.get('model_calls',0)} call(s)",
        f"- Triage types: {by_type}",
        "",
        "## Routes",""]
    for r in sorted(records, key=lambda r: r.get("ts",""), reverse=True):
        route=r.get("route",{}); t=r.get("triage",{})
        title=t.get("title") or (r.get("raw","") or "")[:80].replace("\n"," ")
        lines.append(f"- [{r.get('source')}/{t.get('type','?')}] {title} → {route.get('action','pending')} `{route.get('target','')}`")
    unclear=[r for r in records if r.get("route",{}).get("action")=="unclear"]
    lines += ["","## Unclear (stay at source, labeled)",""]
    lines += ([f"- [{r.get('source')}] {(r.get('raw','') or '')[:80]}" for r in unclear] or ["_none_"])
    lines += ["","## Stale-sweep candidates (propose-only — mailroom never closes these)",""]
    lines += (_stale_lines() if stale else ["_run `mailroom render --stale` to list_"])
    text="\n".join(lines)+"\n"; config.ensure(); config.digest_path().write_text(text); return text

def render_html():
    return "<!doctype html><meta charset=utf-8><title>mailroom</title><style>body{max-width:1000px;margin:2rem auto;font:15px/1.5 system-ui;white-space:pre-wrap;padding:0 1rem}</style><body>"+html.escape(render_markdown())+"</body>"
