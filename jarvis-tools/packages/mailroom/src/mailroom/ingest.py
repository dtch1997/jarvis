from __future__ import annotations
import datetime as dt, time
from . import config, slack, spool, todoist

def ingest(*, now=None) -> dict:
    started=time.monotonic(); config.ensure(); cfg=config.load(); state=spool.load_state(); known=spool.ids()
    now=now or dt.datetime.now(dt.timezone.utc)
    backfill_floor=(now-dt.timedelta(days=config.BACKFILL_DAYS)).timestamp()
    cursors=dict(state.get("slack_cursor") or {})
    reacted=set(state.get("reacted") or [])
    counts={"slack":0,"todoist":0,"voice":0}; discovered={"slack":0,"todoist":0}; errors=[]
    backfill=not bool(state.get("slack_backfill_complete"))
    for channel in cfg.channels:
        # Incremental: after backfill, only fetch since the newest ts we've seen
        # (inclusive re-fetch of the boundary message is deduped by id) so a
        # no-op re-run pulls ~nothing and stays well under the 5 s gate budget.
        oldest=max(backfill_floor, float(cursors.get(channel, 0.0)))
        messages=slack.history(channel, oldest)
        discovered["slack"] += len(messages)
        newest=float(cursors.get(channel, 0.0))
        for m in messages:
            newest=max(newest, float(m["ts"]))
            rid=f"slack:{channel}:{m['ts']}"; files=m.get("files") or []
            audio=next((f for f in files if str(f.get("mimetype","")).startswith("audio/") or f.get("filetype") in {"m4a","mp3","wav","ogg"}),None)
            if rid not in known:
                raw=m.get("text","").strip(); source="slack"; permalink=slack.permalink(channel,m["ts"])
                rec={"id":rid,"source":source,"ts":slack.iso(m["ts"]),"permalink":permalink,"raw":raw,"source_meta":{"channel":channel,"message_ts":m["ts"],"thread_ts":m.get("thread_ts"),"backfill":backfill}}
                if audio:
                    try:
                        transcript,gcs,auto=slack.download_audio(audio,rid.replace(":","_"))
                        rec.update(source="voice",raw=transcript,permalink=gcs,source_permalink=permalink,slack_auto_transcript=auto)
                        counts["voice"]+=1
                    except Exception as e: errors.append(f"audio {rid}: {e}")
                spool.write(rec); known.add(rid); counts["slack"]+=1
            # Loop closure: ✅ once per message, tracked so re-runs never re-hit
            # the reactions API (and a rate-limited partial run resumes cleanly).
            key=f"{channel}:{m['ts']}"
            if key not in reacted:
                try: slack.react(channel,m["ts"]); reacted.add(key); time.sleep(0.4)
                except Exception as e: errors.append(f"react {key}: {e}")
        cursors[channel]=newest
    tasks=todoist.inbox(config.TODOIST_INBOX_ID); discovered["todoist"]=len(tasks)
    if "todoist_baseline" not in state: state["todoist_baseline"]=len(tasks)
    for task in tasks:
        rid=f"todoist:{task['id']}"
        if rid in known: continue
        spool.write({"id":rid,"source":"todoist","ts":task.get("added_at") or now.isoformat(),"permalink":task["id"],"raw":task.get("content","")+(("\n"+task.get("description","")) if task.get("description") else ""),"source_meta":{"task_id":task["id"],"project_id":task.get("project_id"),"labels":task.get("labels",[])}})
        known.add(rid); counts["todoist"]+=1
    elapsed=time.monotonic()-started
    state.update(slack_backfill_complete=True,backfill_start=(now-dt.timedelta(days=config.BACKFILL_DAYS)).date().isoformat(),slack_cursor=cursors,reacted=sorted(reacted),last_ingest={"at":now.isoformat(),"new":counts["slack"]+counts["todoist"],"counts":counts,"discovered":discovered,"elapsed_seconds":round(elapsed,3),"model_calls":0,"errors":errors})
    spool.write_state(state); return state["last_ingest"]

def check() -> tuple[bool,str]:
    state=spool.load_state(); last=state.get("last_ingest",{}); records=spool.load_all()
    source_counts={s:sum(r.get("source") in ({"slack","voice"} if s=="slack" else {s}) for r in records) for s in ("slack","todoist")}
    disc=last.get("discovered",{})
    coverage=all(source_counts.get(s,0)>=disc.get(s,0) for s in disc)
    noop=last.get("new")==0 and last.get("elapsed_seconds",99)<5 and last.get("model_calls")==0
    ok=bool(state.get("slack_backfill_complete")) and coverage and noop and not last.get("errors")
    return ok,f"ingest check: {'OK' if ok else 'FAIL'}; coverage={coverage}; records={source_counts}; discovered={disc}; no-op={noop}; elapsed={last.get('elapsed_seconds')}s; errors={len(last.get('errors',[]))}"
