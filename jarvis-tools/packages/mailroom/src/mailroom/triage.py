from __future__ import annotations
import json, os, subprocess, tempfile

BATCH = 25  # records per claude -p call — bounds output size so JSON stays valid

SCHEMA={"type":"object","properties":{"items":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"type":{"type":"string","enum":["todo","thread-note","research-idea","goal-signal","paper","admin","unclear"]},"title":{"type":"string"},"candidate_slugs":{"type":"array","items":{"type":"string"}},"goal":{"type":["string","null"]},"urgency":{"type":"string","enum":["low","high"]},"target_project":{"type":["string","null"]}},"required":["id","type","title","candidate_slugs","goal","urgency","target_project"],"additionalProperties":False}}},"required":["items"],"additionalProperties":False}

PROMPT="""Triage Daniel's captured thoughts onto existing spines. One item per input id.

Rules:
- todo: an actionable task. Set target_project to EXACTLY one PROJECTS name (never "Inbox"); if none fits, leave target_project null and it stays for review.
- admin: a chore/logistics task; also set a target_project (else null).
- thread-note: names ongoing project work matching a THREAD SLUG (put the slug in candidate_slugs).
- goal-signal: a direction/strategy signal for one GOAL FILE (put its filename in goal).
- research-idea: a research idea with no clear home.
- paper: a paper/arxiv to read.
- unclear: only when nothing above reasonably fits.
Be decisive: prefer a reversible filing (todo/thread-note/research-idea) over unclear. If unsure whether something is a task, call it todo.
Return JSON only, one item per id.

PROJECTS: %s
THREAD SLUGS: %s
GOAL FILES: %s
ITEMS: %s"""

def _call_claude(payload, projects, slugs, goals):
    prompt=PROMPT%(projects,slugs,goals,json.dumps(payload))
    env={**os.environ,"CLAUDE_CONFIG_DIR":os.path.join(tempfile.gettempdir(),"mailroom-claude")}
    p=subprocess.run(["claude","-p",prompt,"--model","haiku","--output-format","json","--json-schema",json.dumps(SCHEMA)],text=True,capture_output=True,env=env,timeout=300)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    outer=json.loads(p.stdout); result=outer.get("structured_output")
    if not result:
        text=outer.get("result",p.stdout); result=json.loads(text)
    return {x["id"]:x for x in result["items"]}, float(outer.get("total_cost_usd") or 0)

def run(records, projects, slugs, goals, max_calls=100, workers=6):
    """Triage records in batches, run concurrently. Returns
    (assignments, cost_usd, calls, truncated). Each haiku call is an independent
    subprocess, so a bounded thread pool collapses the ~N/BATCH cold starts."""
    from concurrent.futures import ThreadPoolExecutor
    batches=[records[i:i+BATCH] for i in range(0, len(records), BATCH)]
    truncated = len(batches) > max_calls
    batches=batches[:max_calls]
    def _do(batch):
        payload=[{"id":r["id"],"source":r["source"],"text":r["raw"][:4000]} for r in batch]
        return _call_claude(payload,projects,slugs,goals)
    assignments={}; cost=0.0; calls=0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for a,c in ex.map(_do, batches):
            assignments.update(a); cost+=c; calls+=1
    return assignments, cost, calls, truncated
