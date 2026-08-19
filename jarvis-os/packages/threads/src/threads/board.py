"""The thread board — **Prompt | Goal | Status**, one row per thread.

The go-to interface for auto-mode work (spec: ``jarvis-os/docs/thread-board.md``).
Where :mod:`threads.dashboard` is an *observational* page about activity, the
board is the working surface: the top of the table is a text box (Enter fires
``threads launch``), each row carries the goal the executor is gated on, and the
Status column is the monitor.

Three principles the code is shaped around:

1. **Row add must be instant.** The board renders optimistically and posts to
   the existing ``POST /launch``; the durable accept is already <100ms with no
   model call, and routing lands on the row asynchronously.
2. **Goal is a field, not a note.** :func:`threads.launch.set_goal` is the
   veto/redirect surface — pre-spawn it re-derives the gate the executor
   receives, post-spawn it is delivered as a ``pool.msg`` and flags the row.
3. **Status is derived, never self-reported.** Every value in the column comes
   from observed state: the intent record, the concierge task record on disk,
   the gate verdict, and the termination sweep's flags. Worker-authored text
   (``result_text``) is deliberately never rendered there — see
   :func:`status_fields`, which is the whitelist.

Rendering is a cheap read of the spool plus a handful of task JSONs: **zero
model calls on page load**, no network beyond localhost.
"""

from __future__ import annotations

import html
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, dashboard, launch, note

# the launcher's termination contract, verbatim (spec: Status column). This is
# the state space of *launched* rows — the ones with an executor to observe.
LIFECYCLE = ("routing", "spawning", "running", "result", "blocked", "failed")
TERMINAL_LIFECYCLE = {"result", "blocked", "failed"}

# observed (scan/weave-born) rows have no executor and no gate, so they get
# their own honest state space rather than being labelled with an executor
# lifecycle they never had: `active` (recent work, nothing parked it),
# `parked`/`closed` (settled — the archive's business), `blocked` (a note says
# it waits on Daniel, which is a needs-you row like any other).
OBSERVED_LIFECYCLE = ("active", "parked", "blocked", "closed")
OBSERVED_SETTLED = {"parked", "closed"}

# concierge task status → board lifecycle. `waiting` is a task parked on an
# external job (signal_waiting): still live work, so it reads as running with
# the pool status shown verbatim next to it.
POOL_LIFECYCLE = {
    "queued": "spawning", "held": "spawning", "running": "running",
    "waiting": "running", "blocked": "blocked", "done": "result",
    "failed": "failed", "cancelled": "failed",
}

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_ts(value):
    return dashboard._parse_ts(value)


def _newest(*values):
    stamps = [v for v in values if v is not None]
    return max(stamps) if stamps else None


# --------------------------------------------------------------------------- #
# the row model
# --------------------------------------------------------------------------- #
@dataclass
class Row:
    """One thread. ``launched`` rows have an intent record; ``observed`` rows
    are reconstructed by scan/weave and carry no launcher goal."""

    key: str
    kind: str                     # "launched" | "observed"
    prompt: str
    slug: str | None = None
    mode: str = ""
    # Goal column
    goal: str = ""
    goal_state: str = launch.GOAL_PENDING
    goal_flagged: bool = False
    goal_msg_error: str = ""
    gate: str = ""
    editable_goal: bool = False
    # Status column (all machine-derived; see status_fields)
    lifecycle: str = "routing"
    pool: dict = field(default_factory=dict)
    pointers: list = field(default_factory=list)   # [(label, href|None)]
    live: tuple | None = None                      # (label, href)
    question: str = ""
    error: str = ""
    violation: bool = False
    disposition: str = ""         # "detached" | "merged" | "dry-run" | ""
    needs_you: bool = False
    terminal: bool = False
    archived: bool = False
    last_activity: datetime | None = None
    created: datetime | None = None
    # detail click-through
    handle: str = ""
    interpretation: str = ""
    notes: list = field(default_factory=list)
    goal_history: list = field(default_factory=list)
    intent_id: str = ""

    @property
    def sort_key(self) -> tuple:
        """needs-you first (violations above blocked), then running by recency,
        then still-spawning work, then terminal rows by recency.

        Launched rows win ties against observed ones: the board is the surface
        for auto-mode work, and observed threads are the context around it.
        """
        if self.needs_you:
            bucket = (0, 0 if self.violation else 1)
        elif self.terminal:
            bucket = (3, 0)
        elif self.lifecycle in ("running", "active"):
            bucket = (1, 0)
        else:
            bucket = (2, 0)
        recency = (self.last_activity or _EPOCH).timestamp()
        return (*bucket, -recency, 0 if self.kind == "launched" else 1, self.key)


@dataclass
class Board:
    rows: list
    generated_at: datetime
    archive_days: int = config.DEFAULT_BOARD_ARCHIVE_DAYS
    candidates: list = field(default_factory=list)
    dash: dashboard.Dashboard | None = None

    @property
    def live(self) -> list:
        return [r for r in self.rows if not r.archived]

    @property
    def archive(self) -> list:
        return [r for r in self.rows if r.archived]

    def counts(self) -> dict:
        out = {name: 0 for name in LIFECYCLE + OBSERVED_LIFECYCLE}
        for r in self.rows:
            out[r.lifecycle] = out.get(r.lifecycle, 0) + 1
        out["needs_you"] = sum(1 for r in self.rows if r.needs_you)
        out["archived"] = len(self.archive)
        out["launched"] = sum(1 for r in self.rows if r.kind == "launched")
        out["observed"] = sum(1 for r in self.rows if r.kind == "observed")
        return out


# --------------------------------------------------------------------------- #
# observed state readers (offline: JSON on disk, nothing else)
# --------------------------------------------------------------------------- #
def pool_view(task: dict | None) -> dict:
    """The observable slice of a concierge task record.

    Deliberately does **not** include ``result_text`` / ``output``: those are
    worker-authored and must never reach the Status column.
    """
    if not task:
        return {}
    attempts = task.get("attempts") or []
    budget = task.get("budget") or {}
    gate_result = task.get("gate_result") or {}
    return {
        "tid": task.get("id") or "",
        "status": task.get("status") or "",
        "detail": task.get("status_detail") or "",
        "attempt": len(attempts),
        "max_attempts": task.get("max_attempts") or 0,
        "cost_usd": sum(a.get("cost_usd") or 0.0 for a in attempts),
        "budget_usd": budget.get("usd"),
        "updated": _parse_ts(task.get("updated")),
        "links": {k: v for k, v in (task.get("links") or {}).items() if v},
        "branch": (task.get("workspace") or {}).get("branch") or "",
        "repo": (task.get("workspace") or {}).get("repo") or "",
        "gate_passed": bool(gate_result.get("passed")),
        "gate_detail": gate_result.get("detail") or "",
        "published": task.get("published") or {},
    }


def log_tail(tid: str, *, lines: int = 120) -> str:
    """The tail of a task's newest attempt log — the fallback 'deepest live
    view' for a row with no stagehand dashboard and no terminal to attach to."""
    base = config.concierge_home() / "logs" / tid
    if not base.is_dir():
        return f"no logs under {base}"
    attempts = sorted((d for d in base.iterdir() if d.is_dir()),
                      key=lambda d: d.name)
    if not attempts:
        return f"no attempt logs under {base}"
    newest = attempts[-1]
    candidates = [newest / "agent.jsonl", newest / "agent.err"]
    candidates += sorted((p for p in newest.iterdir() if p.is_file()),
                         key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            if path.is_file() and path.stat().st_size:
                text = path.read_text(errors="replace").splitlines()
                body = "\n".join(ln[:400] for ln in text[-lines:])
                return f"{path}\n\n{body}"
        except OSError:
            continue
    return f"no readable log in {newest}"


def _deliverable_pointers(rec: dict, pool: dict) -> list:
    """Deliverable pointers for a settled row — every one of them observed:
    gate-reported links, the publish pass's PR, the branch, and the gate's own
    verdict text. Never the worker's prose."""
    out: list = []
    links = pool.get("links") or {}
    for label in ("pr", "report", "dashboard"):
        if links.get(label):
            out.append((label.upper() if label == "pr" else label, links[label]))
    pub = pool.get("published") or {}
    if pub.get("pr_url") and not links.get("pr"):
        out.append(("PR", pub["pr_url"]))
    if pool.get("branch"):
        out.append((f"branch {pool['branch']}", None))
    if pool.get("gate_detail"):
        out.append((f"gate: {pool['gate_detail']}", None))
    # a question-shaped gate's deliverable is a file in the workspace: point at
    # it when it actually exists on disk.
    tid = pool.get("tid")
    if tid:
        answer = config.concierge_home() / "workspaces" / tid / launch.RESULT_FILE
        if answer.is_file():
            out.append((str(answer), None))
    if rec.get("worktree"):
        out.append((f"worktree {rec['worktree']}", None))
    return out


def _live_link(rec: dict, pool: dict) -> tuple | None:
    """The deepest live view available, in order of depth: a stagehand (or other
    worker-published) dashboard, the foyer terminal for a copilot row, the log
    tail otherwise."""
    links = pool.get("links") or {}
    if links.get("dashboard"):
        return ("stagehand dashboard", links["dashboard"])
    if rec.get("mode") == "copilot" and rec.get("foyer_url", "").startswith("http"):
        return ("foyer terminal", rec["foyer_url"])
    tid = pool.get("tid")
    if tid and (config.concierge_home() / "logs" / tid).is_dir():
        return ("log tail", f"tail?tid={tid}")
    return None


# --------------------------------------------------------------------------- #
# status derivation — the whole point of the Status column
# --------------------------------------------------------------------------- #
def status_fields(rec: dict, task: dict | None, *, now: datetime) -> dict:
    """Derive one row's Status column from observed state only.

    Sources, in precedence order: the concierge task record on disk (the
    executor's observed state), then the intent record's own terminal state
    (written by the monitor when the *gate* settles, not by the worker), then
    the presence of an executor handle. The termination sweep's
    ``sweep_flagged_at`` marks a contract violation independently.
    """
    pool = pool_view(task)
    violation = bool(rec.get("sweep_flagged_at"))
    state = rec.get("state") or ""
    terminal_state = rec.get("terminal_state")
    disposition = ""
    if rec.get("dry_run"):
        disposition = "dry-run"
    elif state in ("detached", "merged"):
        disposition = state

    if pool:
        lifecycle = POOL_LIFECYCLE.get(pool["status"], "running")
    elif terminal_state in TERMINAL_LIFECYCLE:
        lifecycle = terminal_state
    elif rec.get("executor_handle"):
        lifecycle = "running" if state == "spawned" else "spawning"
    else:
        lifecycle = "routing"

    # NB the question/error text comes from the *task record's* status_detail —
    # concierge writes it when the gate fails or the worker's mailbox message
    # parks the task. A row with no task record shows no prose at all rather
    # than falling back to a thread note, whose body may quote the worker.
    question = pool.get("detail", "") if lifecycle == "blocked" else ""
    error = ""
    if lifecycle == "failed":
        error = pool.get("detail") or str(rec.get("error") or "")
    pointers = (_deliverable_pointers(rec, pool)
                if lifecycle in TERMINAL_LIFECYCLE else [])
    if disposition == "dry-run":
        pointers = [("dry-run — no executor was spawned", None)]
    live = _live_link(rec, pool) if lifecycle in ("running", "spawning") else None

    needs_you = violation or lifecycle == "blocked"
    terminal = (lifecycle in TERMINAL_LIFECYCLE or disposition in
                ("detached", "dry-run"))
    # created_at is only a fallback: a record that has been updated is dated by
    # its update, otherwise every row would tie on "when it was accepted".
    last = (_newest(pool.get("updated"), _parse_ts(rec.get("updated_at")))
            or _parse_ts(rec.get("created_at")))
    return {
        "lifecycle": lifecycle, "pool": pool, "question": question,
        "error": error, "pointers": pointers, "live": live,
        "violation": violation, "disposition": disposition,
        "needs_you": needs_you, "terminal": terminal, "last_activity": last,
    }


def _prompt_of(t: dashboard.Thread) -> str:
    """An observed thread's Prompt cell: its distilled title."""
    if t.latest_title:
        return t.latest_title
    if t.notes:
        return t.notes[0].get("title") or t.slug
    return t.status_line or t.slug


def observed_row(t: dashboard.Thread, *, now: datetime,
                 cfg: config.Config) -> Row:
    """An observed (scan/weave-born) thread as a board row.

    There is no pool state to observe here, so the lifecycle comes from the
    only records that exist: the registry's closed marker, note statuses, and
    activity recency. Dormant observed rows collapse into the archive rather
    than being labelled with an executor state they never had.
    """
    latest = t.notes[0] if t.notes else {}
    status = (latest.get("status") or "").strip()
    if status == "blocked":
        lifecycle = "blocked"
    elif t.closed:
        lifecycle = "closed"
    elif status in ("parked", "done", "result"):
        lifecycle = "parked" if status == "parked" else "closed"
    else:
        lifecycle = "active"
    needs_you = lifecycle == "blocked"
    pointers = []
    if t.sessions:
        pointers = [(a, None) for a in dashboard._artifact_links(t.sessions[0])]
    row = Row(
        key=f"observed:{t.slug}", kind="observed", prompt=_prompt_of(t),
        slug=t.slug, mode="observed",
        goal="", goal_state=launch.GOAL_PENDING, editable_goal=False,
        lifecycle=lifecycle,
        pointers=pointers,
        question=(latest.get("body", "") if lifecycle == "blocked" else ""),
        needs_you=needs_you,
        terminal=lifecycle in OBSERVED_SETTLED,
        last_activity=t.last_activity, created=t.last_activity,
        notes=t.notes,
        pool={"sessions": t.count, "relevance": t.relevance,
              "status_line": t.status_line},
    )
    # a settled observed thread has nothing in flight to monitor, so it goes
    # straight to the archive; an active one stays live while it is fresh.
    age_days = ((now - t.last_activity).total_seconds() / 86400.0
                if t.last_activity else 1e9)
    row.archived = (not needs_you
                    and (lifecycle in OBSERVED_SETTLED or bool(t.dormant)
                         or age_days > cfg.board_archive_days))
    return row


def launched_row(rec: dict, *, now: datetime, cfg: config.Config,
                 notes_by_slug: dict) -> Row:
    handle = str(rec.get("executor_handle") or "")
    task = (launch.read_task(handle)
            if handle and not handle.startswith(("dry-run:", "thread-")) else None)
    st = status_fields(rec, task, now=now)
    slug = rec.get("resolved_slug")
    notes = notes_by_slug.get(slug or "", [])
    interpretation = next(
        (n.get("body", "") for n in notes
         if n.get("title") == "router interpretation"), "")
    spec = launch.gate_spec_for(rec)
    row = Row(
        key=rec["id"], kind="launched", prompt=rec.get("text") or "",
        slug=slug, mode=rec.get("mode") or "",
        goal=rec.get("goal") or "",
        goal_state=rec.get("goal_state") or launch.GOAL_PENDING,
        goal_flagged=bool(rec.get("goal_flagged")),
        goal_msg_error=str(rec.get("goal_msg_error") or ""),
        gate=spec.get("name", ""), editable_goal=True,
        handle=handle, interpretation=interpretation, notes=notes,
        goal_history=list(rec.get("goal_history") or []),
        intent_id=rec["id"], created=_parse_ts(rec.get("created_at")),
        **{k: st[k] for k in ("lifecycle", "pool", "pointers", "live",
                              "question", "error", "violation", "disposition",
                              "needs_you", "terminal", "last_activity")},
    )
    age_days = ((now - row.last_activity).total_seconds() / 86400.0
                if row.last_activity else 0.0)
    row.archived = (row.terminal and not row.needs_you
                    and age_days > cfg.board_archive_days)
    if row.disposition == "dry-run":
        row.archived = True          # probes never take up board space
    return row


def build(*, now: datetime | None = None, cfg: config.Config | None = None,
          dash: dashboard.Dashboard | None = None, sweep: bool = True) -> Board:
    """Build the board. ``dash`` lets the server reuse its cached dashboard
    model (the expensive part); intents are re-read every time so a row added a
    moment ago is already there."""
    now = now or datetime.now(timezone.utc)
    cfg = cfg or config.load_config()
    dash = dash or dashboard.build(now=now, cfg=cfg, sweep=sweep)

    notes_by_slug: dict[str, list] = {}
    for n in note.load_notes():
        notes_by_slug.setdefault(n["slug"], []).append(n)

    rows: list[Row] = []
    launched_slugs: set[str] = set()
    for rec in launch.load_intents():
        try:
            row = launched_row(rec, now=now, cfg=cfg, notes_by_slug=notes_by_slug)
        except Exception:  # noqa: BLE001 — one bad record never blanks the board
            continue
        rows.append(row)
        if row.slug:
            launched_slugs.add(row.slug)
    for t in dash.threads:
        if t.slug in launched_slugs:
            continue        # already represented by its launched row
        rows.append(observed_row(t, now=now, cfg=cfg))

    rows.sort(key=lambda r: r.sort_key)
    return Board(rows=rows, generated_at=now, archive_days=cfg.board_archive_days,
                 candidates=list(dash.candidates), dash=dash)


# --------------------------------------------------------------------------- #
# candidate-thread delete (the third veto affordance)
# --------------------------------------------------------------------------- #
def delete_candidate(slug: str) -> dict:
    """Delete one agent-drafted candidate thread. Only ever touches
    ``~/.threads/candidates/<slug>.md`` — never a note, summary, or stub."""
    slug = (slug or "").strip().lower()
    if not slug or any(c in slug for c in "/\\ ."):
        raise ValueError(f"bad candidate slug: {slug!r}")
    path = config.candidates_dir() / f"{slug}.md"
    existed = path.is_file()
    if existed:
        path.unlink()
    return {"slug": slug, "deleted": existed}


# --------------------------------------------------------------------------- #
# html — server-rendered, minimal inline JS, phone-usable
# --------------------------------------------------------------------------- #
_CSS = """
*{box-sizing:border-box}
body{font:15px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-width:78rem;
margin:0 auto;padding:.8rem;color:#1a1a1a;background:#fafafa}
h1{font-size:1.25rem;margin:.2rem 0}
a{color:#2563eb}
.sub{color:#888;font-size:12px;margin:.2rem 0 .8rem}
.add{position:sticky;top:0;background:#fafafa;padding:.5rem 0 .6rem;z-index:5;
border-bottom:1px solid #e5e7eb}
.add textarea{width:100%;min-height:3rem;font:inherit;padding:.5rem;
border:1px solid #cbd5e1;border-radius:.4rem;background:#fff;color:inherit}
.add .row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-top:.4rem}
.add input{font:inherit;font-size:13px;padding:.3rem;border:1px solid #cbd5e1;
border-radius:.3rem;background:#fff;color:inherit}
button{font:inherit;font-size:13px;padding:.25rem .6rem;border:1px solid #cbd5e1;
border-radius:.3rem;background:#fff;color:inherit;cursor:pointer}
button.primary{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13px;table-layout:fixed}
th,td{text-align:left;padding:.45rem .5rem;border-bottom:1px solid #e5e7eb;
vertical-align:top;overflow-wrap:anywhere}
th{color:#666;font-weight:600;font-size:11px;text-transform:uppercase;
letter-spacing:.04em}
col.c-prompt{width:38%}col.c-goal{width:31%}col.c-status{width:31%}
tr.needs{background:#fef2f2}
tr.violation{background:#fee2e2;box-shadow:inset 4px 0 0 #b91c1c}
tr.optimistic{background:#eff6ff}
.pill{display:inline-block;padding:0 .4rem;border-radius:.3rem;background:#e5e7eb;
font-size:11px;white-space:nowrap}
.lc-routing{background:#e0e7ff}.lc-spawning{background:#ddd6fe}
.lc-running{background:#d1fae5}.lc-result{background:#bbf7d0}
.lc-blocked{background:#fecaca;font-weight:700}.lc-failed{background:#fecaca}
.lc-active{background:#d1fae5}.lc-parked{background:#e5e7eb}.lc-closed{background:#e5e7eb}
.loud{color:#b91c1c;font-weight:700}
.muted{color:#888}
.q{white-space:pre-wrap;border-left:3px solid #b91c1c;padding-left:.5rem;
margin:.3rem 0;display:block}
.goal-prose{white-space:pre-wrap}
.ptr{display:block;font-size:12px}
details{margin:.25rem 0}summary{cursor:pointer;color:#666;font-size:12px}
code{font-size:12px;background:#eef2ff;padding:0 .2rem;border-radius:.2rem}
.edited{border-left:3px solid #f59e0b;padding-left:.5rem}
.flagged{color:#b45309;font-weight:700}
.acts{margin-top:.35rem;display:flex;gap:.35rem;flex-wrap:wrap}
.arch{margin-top:1.2rem}
@media(max-width:52rem){
  table,thead,tbody,tr,td,th{display:block;width:100%}
  thead{display:none}
  tr{border:1px solid #e5e7eb;border-radius:.4rem;margin:.5rem 0;background:#fff;
  padding:.2rem .1rem}
  td{border:none;border-bottom:1px dashed #eee}
  td:last-child{border-bottom:none}
  td::before{content:attr(data-col);display:block;color:#888;font-size:10px;
  text-transform:uppercase;letter-spacing:.04em}
}
@media(prefers-color-scheme:dark){
  body{background:#111;color:#ddd}.add{background:#111;border-color:#333}
  .add textarea,.add input,button{background:#1b1b1b;border-color:#333;color:#ddd}
  th,td{border-color:#262626}.pill{background:#262626}
  tr.needs{background:#2a1414}tr.violation{background:#3a1414}
  tr.optimistic{background:#12233d}
  .lc-routing{background:#25306b;color:#e0e7ff}.lc-spawning{background:#3b2a6b;color:#ddd6fe}
  .lc-running{background:#0f3d2e;color:#a7f3d0}.lc-result{background:#14532d;color:#bbf7d0}
  .lc-blocked{background:#7f1d1d;color:#fee2e2}.lc-failed{background:#7f1d1d;color:#fee2e2}
  .lc-active{background:#0f3d2e;color:#a7f3d0}
  code{background:#1f2937}
  @media(max-width:52rem){tr{background:#181818;border-color:#333}}
}
"""

_JS = """
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
async function addRow(ev){
  if(ev){ev.preventDefault();}
  var ta=document.getElementById('add-text');var text=ta.value.trim();
  if(!text){return false;}
  var body={text:text,
            mode:document.getElementById('add-copilot').checked?'copilot':'full-auto',
            slug:document.getElementById('add-slug').value||null};
  // optimistic row first — the send contract guarantees the durable accept,
  // so the row is honest before the response lands.
  var tb=document.getElementById('rows');
  var tr=document.createElement('tr');tr.className='optimistic';
  tr.innerHTML="<td data-col='prompt'>"+esc(text)+"</td>"+
    "<td data-col='goal'><span class='muted'>drafting…</span></td>"+
    "<td data-col='status'><span class='pill lc-routing'>accepting</span></td>";
  tb.insertBefore(tr,tb.firstChild);
  ta.value='';ta.focus();
  try{
    var r=await fetch('launch',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var j=await r.json();
    tr.children[2].innerHTML=r.ok
      ?"<span class='pill lc-routing'>routing</span> <span class='muted'>"+esc(j.id)+"</span>"
      :"<span class='loud'>error: "+esc(j.error||String(r.status))+"</span>";
    if(r.ok){setTimeout(function(){location.reload();},6000);}
  }catch(e){tr.children[2].innerHTML="<span class='loud'>error: "+esc(String(e))+"</span>";}
  return false;
}
function addKey(ev){
  if(ev.key==='Enter'&&!ev.shiftKey){ev.preventDefault();addRow(null);}
}
function editGoal(id,on){
  document.getElementById('gv-'+id).hidden=on;
  document.getElementById('gf-'+id).hidden=!on;
  if(on){document.getElementById('gt-'+id).focus();}
}
async function saveGoal(ev,id){
  ev.preventDefault();
  var text=document.getElementById('gt-'+id).value;
  var r=await fetch('goal',{method:'POST',headers:{'Content-Type':'application/json'},
                            body:JSON.stringify({id:id,goal:text})});
  if(!r.ok){var j=await r.json();alert('goal edit failed: '+(j.error||r.status));return false;}
  location.reload();return false;
}
async function rowAction(path,id,slug){
  if(path==='merge'){slug=prompt('Merge into which thread slug?');if(!slug){return;}}
  if(path==='candidate-delete'&&!confirm('Delete candidate thread '+slug+'?')){return;}
  await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({id:id,slug:slug})});
  location.reload();
}
"""


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _ago(then: datetime | None, now: datetime) -> str:
    if then is None:
        return "—"
    secs = max(0.0, (now - then).total_seconds())
    if secs < 90:
        return f"{int(secs)}s ago"
    if secs < 5400:
        return f"{int(secs // 60)}m ago"
    if secs < 172800:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def _add_form(board: Board) -> str:
    slugs = sorted({r.slug for r in board.rows if r.slug})
    datalist = "".join(f"<option value='{_esc(s)}'>" for s in slugs)
    return (
        "<form class='add' onsubmit='return addRow(event)'>"
        "<textarea id='add-text' onkeydown='addKey(event)' autofocus "
        "placeholder='What do you want done? — Enter fires the thread "
        "(shift+Enter for a newline)'></textarea>"
        "<div class='row'>"
        "<button class='primary' type='submit'>send</button>"
        "<label><input id='add-copilot' type='checkbox'> copilot"
        " <span class='muted'>(default full-auto)</span></label>"
        "<input id='add-slug' list='board-slugs' placeholder='pin a slug (optional)'>"
        f"<datalist id='board-slugs'>{datalist}</datalist>"
        "</div></form>")


def _goal_cell(row: Row) -> str:
    if not row.editable_goal:
        note_hint = (f"{len(row.notes)} note(s)" if row.notes else "no notes")
        return ("<span class='muted'>observed thread — no launcher goal "
                f"({note_hint}). Resume with <code>threads pickup "
                f"{_esc(row.slug)}</code></span>")
    rid = _esc(row.key)
    if row.goal:
        prose = f"<span class='goal-prose'>{_esc(row.goal)}</span>"
    else:
        prose = "<span class='muted'>drafting… (router is routing this row)</span>"
    cls = " edited" if row.goal_state == launch.GOAL_EDITED else ""
    marks = ""
    if row.goal_state == launch.GOAL_EDITED:
        marks += " <span class='pill'>edited</span>"
    if row.goal_flagged:
        marks += (" <span class='flagged'>⚑ edited after spawn — worker "
                  "notified, may still be on the old goal</span>")
    if row.goal_msg_error:
        marks += f" <span class='flagged'>⚑ {_esc(row.goal_msg_error)}</span>"
    out = [f"<div id='gv-{rid}' class='goal{cls}'>{prose}{marks}",
           f"<details><summary>gate</summary><code>{_esc(row.gate)}</code>"
           "</details>",
           f"<div class='acts'><button onclick=\"editGoal('{rid}',true)\">"
           "edit goal</button></div></div>",
           f"<form id='gf-{rid}' hidden onsubmit=\"return saveGoal(event,'{rid}')\">"
           f"<textarea id='gt-{rid}' rows='5' style='width:100%;font:inherit'>"
           f"{_esc(row.goal)}</textarea>"
           "<div class='acts'><button class='primary' type='submit'>save</button>"
           f"<button type='button' onclick=\"editGoal('{rid}',false)\">cancel"
           "</button></div></form>"]
    return "".join(out)


def _status_cell(row: Row, now: datetime) -> str:
    """Render the Status column from :func:`status_fields`' output only."""
    pool = row.pool or {}
    out = [f"<span class='pill lc-{_esc(row.lifecycle)}'>{_esc(row.lifecycle)}"
           "</span>"]
    if row.violation:
        out.append(" <span class='loud'>⚠ TERMINATION CONTRACT VIOLATED — "
                   "dormant past the deadline with no terminal note</span>")
    if row.disposition:
        out.append(f" <span class='pill'>{_esc(row.disposition)}</span>")
    out.append(f" <span class='muted'>{_esc(_ago(row.last_activity, now))}</span>")
    if row.kind == "launched" and pool.get("status"):
        bits = [f"pool {pool['status']}"]
        if pool.get("attempt"):
            bits.append(f"attempt {pool['attempt']}/{pool.get('max_attempts') or '?'}")
        if pool.get("cost_usd") is not None:
            budget = (f"/${pool['budget_usd']:.2f}"
                      if isinstance(pool.get("budget_usd"), (int, float)) else "")
            bits.append(f"${pool['cost_usd']:.2f}{budget}")
        out.append(f"<span class='ptr muted'>{_esc(' · '.join(bits))}</span>")
    elif row.kind == "observed":
        out.append(f"<span class='ptr muted'>{pool.get('sessions', 0)} observed "
                   f"session(s) · rel {pool.get('relevance', 0.0):.2f}</span>")
    if row.live:
        label, href = row.live
        out.append(f"<span class='ptr'>▸ <a href='{_esc(href)}'>{_esc(label)}"
                   "</a></span>")
    if row.question:
        out.append(f"<span class='q'>{_esc(row.question)}</span>")
    if row.error:
        out.append(f"<span class='q'>{_esc(row.error)}</span>")
    for label, href in row.pointers:
        if href:
            out.append(f"<span class='ptr'>→ <a href='{_esc(href)}'>"
                       f"{_esc(label)}</a></span>")
        else:
            out.append(f"<span class='ptr muted'>→ {_esc(label)}</span>")
    return "".join(out)


def _prompt_cell(row: Row) -> str:
    out = []
    if row.kind == "observed":
        out.append("<span class='pill'>observed</span> ")
    out.append(f"<b>{_esc(row.prompt)}</b>")
    meta = [row.slug or "routing…"]
    if row.mode:
        meta.append(row.mode)
    out.append(f"<div class='muted'>{_esc(' · '.join(meta))}</div>")
    # click-through detail: note history, interpretation, executor handles.
    out.append("<details><summary>detail</summary>")
    if row.intent_id:
        out.append(f"<div class='muted'>intent <code>{_esc(row.intent_id)}</code>"
                   + (f" · executor <code>{_esc(row.handle)}</code>"
                      if row.handle else "") + "</div>")
    if row.pool.get("repo"):
        out.append(f"<div class='muted'>repo {_esc(row.pool['repo'])}</div>")
    if row.interpretation:
        out.append("<div><b>interpretation</b><span class='goal-prose'>\n"
                   f"{_esc(row.interpretation)}</span></div>")
    if row.goal_history:
        out.append("<div><b>goal edits</b>")
        for h in row.goal_history[-5:]:
            out.append(f"<div class='muted'>{_esc(h.get('at', ''))} "
                       f"({_esc(h.get('phase', ''))}): {_esc(h.get('text', ''))}"
                       "</div>")
        out.append("</div>")
    out.append(f"<div><b>notes ({len(row.notes)})</b>")
    for n in row.notes[:8]:
        status = f" [{n['status']}]" if n.get("status") else ""
        out.append(f"<div class='muted'>{_esc(n.get('created', '')[:16])}"
                   f"{_esc(status)} — {_esc(n.get('title', ''))}</div>")
    out.append("</div></details>")
    if row.kind == "launched":
        rid = _esc(row.key)
        out.append(
            "<div class='acts'>"
            f"<button onclick=\"rowAction('detach','{rid}',null)\">detach</button>"
            f"<button onclick=\"rowAction('merge','{rid}',null)\">merge into "
            "thread</button></div>")
    return "".join(out)


def _table(rows: list, now: datetime, *, tbody_id: str = "") -> str:
    out = ["<table><colgroup><col class='c-prompt'><col class='c-goal'>"
           "<col class='c-status'></colgroup>"
           "<thead><tr><th>Prompt</th><th>Goal</th><th>Status</th></tr></thead>",
           f"<tbody{f' id={tbody_id}' if tbody_id else ''}>"]
    for row in rows:
        cls = []
        if row.violation:
            cls.append("violation")
        elif row.needs_you:
            cls.append("needs")
        out.append(f"<tr class='{' '.join(cls)}'>"
                   f"<td data-col='prompt'>{_prompt_cell(row)}</td>"
                   f"<td data-col='goal'>{_goal_cell(row)}</td>"
                   f"<td data-col='status'>{_status_cell(row, now)}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_html(board: Board | None = None, *, now: datetime | None = None,
                refresh: int | None = None) -> str:
    board = board or build(now=now)
    now = board.generated_at
    counts = board.counts()
    meta_refresh = (f"<meta http-equiv='refresh' content='{int(refresh)}'>"
                    if refresh else "")
    out = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        meta_refresh,
        "<title>thread board</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>thread board</h1>",
        f"<div class='sub'>{len(board.live)} live row(s) · "
        f"<b>{counts['needs_you']} need you</b> · launched: "
        f"{counts['routing'] + counts['spawning']} starting, "
        f"{counts['running']} running, {counts['result']} result, "
        f"{counts['blocked']} blocked, {counts['failed']} failed · observed: "
        f"{counts['active']} active · {counts['archived']} archived "
        f"(settled, or older than {board.archive_days}d) · "
        "<a href='dashboard'>activity dashboard →</a></div>",
        _add_form(board),
    ]
    if not board.live:
        out.append("<p class='muted'>no live rows — send an intent above.</p>")
    else:
        out.append(_table(board.live, now, tbody_id="rows"))
    if board.archive:
        out.append(f"<details class='arch'><summary>archive — "
                   f"{len(board.archive)} row(s): settled, parked, or older "
                   f"than {board.archive_days}d</summary>")
        out.append(_table(board.archive, now))
        out.append("</details>")
    if board.candidates:
        out.append("<details class='arch'><summary>candidate threads — "
                   f"{len(board.candidates)} agent-drafted, standing until "
                   "Daniel edits</summary>")
        for c in board.candidates:
            slug = _esc(c["slug"])
            out.append(
                f"<div><b>{_esc(c['name'])}</b> "
                f"<span class='muted'>{len(c['members'])} session(s)</span> "
                f"<button onclick=\"rowAction('candidate-delete',null,'{slug}')\">"
                "delete</button></div>")
        out.append("</details>")
    out.append(f"<p class='muted'>generated {now.isoformat(timespec='seconds')} "
               "· status is derived from observed state (intent records, pool "
               "state, gate verdicts, sweep flags) — never a worker's "
               "self-report</p>")
    out.append(f"<script>{_JS}</script>")
    out.append("</body></html>")
    return "\n".join(out)


def render_text(board: Board | None = None, *, now: datetime | None = None) -> str:
    """The board as plain text (``threads board``) — same rows, same order."""
    board = board or build(now=now)
    now = board.generated_at
    counts = board.counts()
    lines = [f"thread board — {len(board.live)} live row(s), "
             f"{counts['needs_you']} need you, {counts['archived']} archived",
             ""]
    for row in board.live:
        flag = "!!" if row.violation else ("!" if row.needs_you else " ")
        lines.append(f"{flag} [{row.lifecycle:<8}] {row.prompt[:64]}")
        lines.append(f"     goal: {(row.goal or '(drafting…)')[:100]}")
        lines.append(f"     gate: {row.gate or '—'}")
        detail = []
        if row.pool.get("status"):
            detail.append(f"pool {row.pool['status']}")
        if row.question:
            detail.append(f"question: {row.question[:80]}")
        if row.error:
            detail.append(f"error: {row.error[:80]}")
        for label, _href in row.pointers[:3]:
            detail.append(str(label)[:80])
        if detail:
            lines.append("     " + " · ".join(detail))
        lines.append("")
    if board.archive:
        lines.append(f"archive: {len(board.archive)} row(s) — settled, parked, "
                     f"or older than {board.archive_days}d")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# ``threads board --check`` — the offline gate
# --------------------------------------------------------------------------- #
class _ModelCallForbidden(RuntimeError):
    pass


def _no_model_runner(*_a, **_k):
    raise _ModelCallForbidden(
        "the board made a model call during a render (page loads must be free)")


class _Checks:
    """A tiny assertion recorder, so the gate reports *what* it verified."""

    def __init__(self):
        self.lines: list[str] = []
        self.failures = 0

    def ok(self, condition, label: str, detail: str = "") -> bool:
        good = bool(condition)
        if not good:
            self.failures += 1
        self.lines.append(f"  {'PASS' if good else 'FAIL'}  {label}"
                          + (f" — {detail}" if detail else ""))
        return good

    def section(self, title: str) -> None:
        self.lines.append(title)


def _fixture_task(home: Path, tid: str, *, status: str, detail: str = "",
                  attempts: int = 1, cost: float = 0.0, gate_passed=None,
                  links: dict | None = None, result_text: str = "",
                  updated: str = "") -> dict:
    """Write a concierge task record into a fixture home. Mirrors the fields the
    board reads (``concierge.records.new_task``'s shape)."""
    task = {
        "id": tid, "title": f"thread launch: {tid}",
        "workspace": {"repo": "/tmp/fixture-repo", "branch": f"fix/{tid}"},
        "gate": {"kind": "shell_ok", "cmd": "test -s .threads-result.md"},
        "budget": {"usd": 20.0, "wall_minutes": 240.0},
        "status": status, "status_detail": detail,
        "attempts": [{"n": i + 1, "cost_usd": cost} for i in range(attempts)],
        "max_attempts": 3, "result_text": result_text,
        "links": links or {"pr": None, "report": None, "dashboard": None},
        "gate_result": (None if gate_passed is None else
                        {"passed": gate_passed, "detail": f"gate verdict {tid}"}),
        "created": "2026-08-18T00:00:00", "updated": updated or "2026-08-18T01:00:00",
    }
    d = home / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{tid}.json").write_text(json.dumps(task))
    return task


def _spawned_fixture(text: str, *, tid: str, slug: str, mode: str = "full-auto",
                     state: str = "spawned", terminal: str | None = None,
                     created: str | None = None, updated: str | None = None,
                     flagged: str | None = None) -> dict:
    """A launched, spawned intent record in the fixture spool."""
    rec = launch.accept(text, mode=mode, slug=slug, enqueue=False)
    saved = launch.load_intent(rec["id"])
    saved.update(resolved_slug=slug, route="pinned", state=state,
                 executor_handle=tid, terminal_state=terminal,
                 goal=launch.fallback_goal(text, launch.gate_spec_for(saved)),
                 goal_state=launch.GOAL_DRAFTED)
    if created or updated:
        saved["created_at"] = created or updated
    if updated:
        saved["updated_at"] = updated
    if flagged:
        saved["sweep_flagged_at"] = flagged
    launch._write(saved)
    return saved


def _check_lifecycles(c: _Checks, now: datetime) -> None:
    """Every lifecycle state, derived from fixture records."""
    c.section("status derivation (fixtures, one per lifecycle state):")
    home = config.concierge_home()
    cases = [
        ("routing", dict(state="accepted", handle=None, task=None)),
        ("spawning", dict(state="spawned", handle="t-fix-queued",
                          task=dict(status="queued"))),
        ("running", dict(state="spawned", handle="t-fix-running",
                         task=dict(status="running", attempts=1, cost=0.42))),
        ("running", dict(state="spawned", handle="t-fix-waiting",
                         task=dict(status="waiting", detail="waiting: pod job"))),
        ("result", dict(state="terminal", handle="t-fix-done",
                        task=dict(status="done", gate_passed=True,
                                  detail="shell_ok rc=0",
                                  links={"pr": "https://example.invalid/pr/1"}))),
        ("blocked", dict(state="spawned", handle="t-fix-blocked",
                         task=dict(status="blocked",
                                   detail="Which bucket should results go to?"))),
        ("failed", dict(state="spawned", handle="t-fix-failed",
                        task=dict(status="failed",
                                  detail="gate failed after 3 attempts"))),
    ]
    for expect, spec in cases:
        tid = spec["handle"]
        if spec["task"]:
            _fixture_task(home, tid, **spec["task"])
        rec = {"id": "01FIXTURE", "text": "fixture intent", "mode": "full-auto",
               "state": spec["state"], "executor_handle": tid,
               "resolved_slug": "fixture", "created_at": now.isoformat(),
               "updated_at": now.isoformat(),
               "terminal_state": "result" if spec["state"] == "terminal" else None}
        st = status_fields(rec, launch.read_task(tid) if tid else None, now=now)
        c.ok(st["lifecycle"] == expect,
             f"{spec['task']['status'] if spec['task'] else 'no task'} → {expect}",
             f"got {st['lifecycle']}")
    # blocked renders the actual question; result renders deliverable pointers
    blocked = status_fields(
        {"state": "spawned", "executor_handle": "t-fix-blocked",
         "updated_at": now.isoformat()},
        launch.read_task("t-fix-blocked"), now=now)
    c.ok("Which bucket" in blocked["question"], "blocked row carries the question")
    done = status_fields(
        {"state": "terminal", "executor_handle": "t-fix-done",
         "terminal_state": "result", "updated_at": now.isoformat()},
        launch.read_task("t-fix-done"), now=now)
    c.ok(any(h == "https://example.invalid/pr/1" for _l, h in done["pointers"]),
         "result row renders deliverable pointers inline")
    running = status_fields(
        {"state": "spawned", "executor_handle": "t-fix-running",
         "updated_at": now.isoformat()},
        launch.read_task("t-fix-running"), now=now)
    c.ok(running["pool"].get("cost_usd") == 0.42 and running["pool"]["attempt"] == 1,
         "running row carries pool status + attempt + cost")
    # a contract violation is loud and pins to the top
    viol = status_fields(
        {"state": "spawned", "executor_handle": "t-fix-running",
         "sweep_flagged_at": now.isoformat(), "updated_at": now.isoformat()},
        launch.read_task("t-fix-running"), now=now)
    c.ok(viol["violation"] and viol["needs_you"],
         "sweep-flagged row is a needs-you violation")


def _check_purity(c: _Checks, now: datetime) -> None:
    c.section("status column purity (no worker self-report):")
    token = "WORKER-SELF-REPORTED-SUCCESS-DO-NOT-RENDER"
    _fixture_task(config.concierge_home(), "t-fix-purity", status="done",
                  gate_passed=True, detail="shell_ok rc=0", result_text=token)
    rec = {"id": "01PURITY", "text": "fixture", "mode": "full-auto",
           "state": "terminal", "terminal_state": "result",
           "executor_handle": "t-fix-purity", "updated_at": now.isoformat()}
    st = status_fields(rec, launch.read_task("t-fix-purity"), now=now)
    row = Row(key="p", kind="launched", prompt="fixture", gate="g",
              **{k: st[k] for k in ("lifecycle", "pool", "pointers", "live",
                                    "question", "error", "violation",
                                    "disposition", "needs_you", "terminal",
                                    "last_activity")})
    cell = _status_cell(row, now)
    c.ok(token not in cell, "worker result_text never reaches the Status cell")
    c.ok(token not in json.dumps(st, default=str),
         "worker result_text is not even in the derived status fields")
    c.ok("gate verdict" in cell or "shell_ok" in cell,
         "the gate's own verdict is what the settled row shows")


def _check_sort(c: _Checks, now: datetime) -> Board:
    c.section("needs-you sort + archive collapse:")
    old = (now - timedelta(days=30)).isoformat()
    recent = (now - timedelta(minutes=5)).isoformat()
    older = (now - timedelta(hours=6)).isoformat()
    home = config.concierge_home()
    _fixture_task(home, "t-sort-run1", status="running", updated=recent)
    _fixture_task(home, "t-sort-run2", status="running", updated=older)
    _fixture_task(home, "t-sort-block", status="blocked",
                  detail="need a decision", updated=older)
    _fixture_task(home, "t-sort-done", status="done", gate_passed=True,
                  detail="ok", updated=old)
    _spawned_fixture("fresh running work", tid="t-sort-run1", slug="sort-run1",
                     updated=recent)
    _spawned_fixture("older running work", tid="t-sort-run2", slug="sort-run2",
                     updated=older)
    _spawned_fixture("blocked work", tid="t-sort-block", slug="sort-block",
                     updated=older)
    _spawned_fixture("settled work", tid="t-sort-done", slug="sort-done",
                     state="terminal", terminal="result", created=old, updated=old)
    _spawned_fixture("violating work", tid="t-sort-viol", slug="sort-viol",
                     created=old, updated=old, flagged=now.isoformat())

    board = build(now=now, sweep=False)
    order = [r.slug for r in board.live]
    c.ok(order[:2] == ["sort-viol", "sort-block"],
         "violations then blocked pin to the top", f"got {order[:2]}")
    c.ok(order[2:4] == ["sort-run1", "sort-run2"],
         "running rows follow, most recent first", f"got {order[2:4]}")
    c.ok("sort-done" not in order,
         "settled rows older than archive_days collapse into the archive")
    c.ok("sort-done" in [r.slug for r in board.archive],
         "the archived row is still reachable in the archive section")
    c.ok("archive —" in render_html(board),
         "the archive section is labelled and counted (never a silent drop)")
    c.ok(all(not r.archived for r in board.rows if r.needs_you),
         "needs-you rows are never archived, however old")
    html_page = render_html(board)
    c.ok("thread board" in html_page and "Prompt" in html_page
         and "Goal" in html_page and "Status" in html_page,
         "board renders the three columns")
    c.ok("TERMINATION CONTRACT VIOLATED" in html_page,
         "contract-violation rows render loud")
    c.ok("need a decision" in html_page, "the blocked question renders inline")
    c.ok("viewport" in html_page and "max-width:52rem" in html_page,
         "page is responsive (viewport meta + stacked-row media query)")
    return board


def _check_goal_edit(c: _Checks, now: datetime) -> None:
    c.section("goal cell: draft, pre-spawn re-derivation, post-spawn delivery:")
    # 1. pre-spawn edit re-derives the gate the executor is submitted against.
    rec = launch.accept("what is the median latency of the fleet?",
                        slug="goal-pre", enqueue=False)
    spec0 = launch.gate_spec_for(launch.load_intent(rec["id"]))
    c.ok(spec0["kind"] == "shell_ok",
         "question-shaped intent gets the result-file gate", spec0["name"])
    edited = launch.set_goal(
        rec["id"], "Deliverables: a PR that implements the latency probe.\n\n"
                   "Done when: an open PR exists on the launch branch.")
    spec1 = launch.gate_spec_for(edited)
    c.ok(spec1["kind"] == "pr_open",
         "pre-spawn goal edit re-derives the gate", spec1["name"])
    c.ok(edited["goal_state"] == launch.GOAL_EDITED, "the edit is recorded")
    seed = launch._spec_seed(edited, "goal-pre", "interpretation")
    c.ok("implements the latency probe" in seed and spec1["name"] in seed,
         "the executor's spec seed carries the edited goal + re-derived gate")
    try:
        gate = launch.gate_object(spec1)
        c.ok(type(gate).__name__ == "PrOpen",
             "the concierge gate object built for the executor is PrOpen",
             type(gate).__name__)
    except Exception as exc:  # noqa: BLE001 — concierge absent is a real answer
        c.ok(False, "the concierge gate object builds", str(exc))
    # the router must not clobber a human edit when it lands later
    routed = launch.process_intent(rec["id"], runner=launch._offline_runner)
    c.ok(routed["goal_state"] == launch.GOAL_EDITED
         and "latency probe" in routed["goal"],
         "async routing never overwrites an edited goal (draft-and-veto)")
    c.ok(launch.gate_spec_for(routed)["kind"] == "pr_open",
         "and the re-derived gate survives routing")

    # 2. a drafted goal is derivation-stable: saving it unedited must not
    #    silently re-spec the gate.
    for text in ("what is the median latency of the fleet?",
                 "implement the retry path and open a PR",
                 "run the sweep and write results.jsonl, then open a PR"):
        spec = launch.gate_spec(None, text)
        again = launch.gate_spec(launch.fallback_goal(text, spec), text)
        c.ok(again["kind"] == spec["kind"],
             f"drafted goal is derivation-stable ({spec['kind']})",
             f"{spec['kind']} → {again['kind']}")

    # 3. post-spawn edit lands as pool.msg and flags the row.
    _fixture_task(config.concierge_home(), "t-goal-post", status="running")
    post = _spawned_fixture("implement the parser", tid="t-goal-post",
                            slug="goal-post")
    edited2 = launch.set_goal(post["id"], "Deliverables: the parser, plus a "
                                          "regression test. Done when: an open "
                                          "PR exists on the launch branch.")
    c.ok(edited2.get("goal_flagged") is True,
         "post-spawn edit flags the row")
    mailbox = config.concierge_home() / "mailbox" / "t-goal-post.jsonl"
    delivered = mailbox.read_text() if mailbox.is_file() else ""
    c.ok("regression test" in delivered and not edited2.get("goal_msg_error"),
         "post-spawn edit is delivered to the worker as pool.msg",
         edited2.get("goal_msg_error", ""))

    # 4. an edit after the gate has passed does not rewrite settled history.
    _fixture_task(config.concierge_home(), "t-goal-settled", status="done",
                  gate_passed=True, detail="shell_ok rc=0")
    settled = _spawned_fixture("write the summary", tid="t-goal-settled",
                               slug="goal-settled", state="terminal",
                               terminal="result")
    before = launch.gate_spec_for(settled)
    after = launch.set_goal(settled["id"], "Deliverables: open a PR instead.")
    c.ok(launch.gate_spec_for(after)["kind"] == before["kind"],
         "an edit after the gate passed does not re-derive the gate")

    # 5. the board surfaces the flag and the edited prose.
    page = render_html(build(now=now, sweep=False))
    c.ok("regression test" in page, "the edited goal renders in the Goal cell")
    c.ok("edited after spawn" in page, "the post-spawn discrepancy is flagged")
    c.ok("gf-" in page and "saveGoal" in page,
         "the Goal cell is inline-editable (edit form + save handler)")


def _check_row_add(c: _Checks, now: datetime) -> None:
    """The real HTTP surface: default page, row add, dashboard secondary."""
    c.section("serving: default page, row add (optimistic + durable), routes:")
    import http.client

    from . import server
    os.environ["THREADS_DISABLE_ENQUEUE"] = "1"   # accept, never route/spawn
    srv = server.serve(tunnel=False, interval=3600)
    try:
        port = int(srv.local_url.rsplit(":", 1)[1])

        def request(method, path, body=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            payload = json.dumps(body) if body is not None else None
            conn.request(method, path, body=payload,
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, resp.read().decode()

        status, page = request("GET", "/")
        c.ok(status == 200 and "<h1>thread board</h1>" in page,
             "the board is the default page at the threads URL")
        c.ok("addRow" in page and "add-text" in page,
             "the default page carries the top-of-table add box")
        d_status, d_page = request("GET", "/dashboard")
        c.ok(d_status == 200 and "activity dashboard" in d_page,
             "the observational dashboard stays reachable as a second page")
        c.ok("dashboard" in page, "the board links to it")

        text = "board --check synthetic row add probe"
        t0 = time.perf_counter()
        status, body = request("POST", "/launch", {"text": text})
        latency_ms = (time.perf_counter() - t0) * 1000
        rec = json.loads(body)
        c.ok(status == 202, "POST /launch accepts", f"status {status}")
        c.ok(latency_ms < 100, "row add is durable in <100ms",
             f"{latency_ms:.1f} ms round-trip")
        c.ok(bool(rec.get("gate", {}).get("kind")),
             "the accepted row already carries its literal gate")
        status, page = request("GET", "/")
        c.ok(text in page, "the added row is on the board")
        c.ok("drafting…" in page or "routing" in page,
             "its Goal cell shows the async draft in flight")

        # veto affordances are wired to the endpoints
        status, _ = request("POST", "/goal", {"id": rec["id"],
                                              "goal": "Deliverables: probe."})
        c.ok(status == 200, "POST /goal edits the goal cell", f"status {status}")
        status, _ = request("POST", "/detach", {"id": rec["id"]})
        c.ok(status == 200, "POST /detach is wired", f"status {status}")
        status, _ = request("POST", "/merge", {"id": rec["id"],
                                              "slug": "board-check"})
        c.ok(status == 200, "POST /merge is wired", f"status {status}")
        (config.candidates_dir()).mkdir(parents=True, exist_ok=True)
        (config.candidates_dir() / "cand-probe.md").write_text("# cand\n- x\n")
        status, _ = request("POST", "/candidate-delete", {"slug": "cand-probe"})
        c.ok(status == 200
             and not (config.candidates_dir() / "cand-probe.md").exists(),
             "POST /candidate-delete removes the candidate thread")
        status, tail = request("GET", "/tail?tid=t-fix-running")
        c.ok(status == 200, "the log-tail view serves", f"status {status}")
    finally:
        srv.stop()
        os.environ.pop("THREADS_DISABLE_ENQUEUE", None)


def board_check() -> tuple[bool, str]:
    """Offline gate for the board (no model calls, no network beyond localhost).

    Two halves: the **real spool** is rendered read-only (never mutated — the
    termination sweep is off and no intent is written), then every write-shaped
    assertion runs against a **fixture spool** in a temp dir. A model call
    anywhere in a render is a failure, not a slowdown.
    """
    import tempfile

    from . import summarize

    c = _Checks()
    now = datetime.now(timezone.utc)

    # ---- half 1: the real spool, read-only, with model calls forbidden ----
    c.section(f"real spool ({config.threads_dir()}), read-only:")
    real_runner, summarize.default_runner = summarize.default_runner, _no_model_runner
    try:
        board = build(now=now, sweep=False)
        page = render_html(board)
        c.ok(len(page) > 500, "real-spool board renders",
             f"{len(board.rows)} row(s), {len(page)} bytes")
        c.ok(all(r.lifecycle in LIFECYCLE for r in board.rows
                 if r.kind == "launched"),
             "every launched row has a lifecycle from the termination contract")
        c.ok(all(r.lifecycle in OBSERVED_LIFECYCLE for r in board.rows
                 if r.kind == "observed"),
             "every observed row has one of the observed states")
        c.ok(board.live == sorted(board.live, key=lambda r: r.sort_key),
             "real rows come out in board order")
        c.ok(render_text(board) is not None, "the text rendering works too")
    except _ModelCallForbidden as exc:
        c.ok(False, "zero model calls on page load", str(exc))
    except Exception as exc:  # noqa: BLE001
        c.ok(False, "real-spool board renders", f"{type(exc).__name__}: {exc}")
    finally:
        summarize.default_runner = real_runner
    c.ok(True, "zero model calls on page load (runner stubbed to raise)")

    # ---- half 2: fixtures, in a throwaway spool ----
    saved_env = {k: os.environ.get(k)
                 for k in ("THREADS_HOME", "THREADS_CONCIERGE_HOME",
                           "THREADS_MEMORY_DIR", "THREADS_PROJECTS_DIR",
                           "THREADS_GOALS_DIR", "THREADS_DISABLE_ENQUEUE")}
    with tempfile.TemporaryDirectory(prefix="threads-board-check-") as tmp:
        root = Path(tmp)
        for name, key in (("home", "THREADS_HOME"),
                          ("concierge-home", "THREADS_CONCIERGE_HOME"),
                          ("memory", "THREADS_MEMORY_DIR"),
                          ("projects", "THREADS_PROJECTS_DIR"),
                          ("goals", "THREADS_GOALS_DIR")):
            (root / name).mkdir(parents=True, exist_ok=True)
            os.environ[key] = str(root / name)
        config.ensure_spool()
        try:
            _check_lifecycles(c, now)
            _check_purity(c, now)
            _check_sort(c, now)
            _check_goal_edit(c, now)
            _check_row_add(c, now)
        except Exception as exc:  # noqa: BLE001 — a crash is a gate failure
            import traceback
            c.ok(False, "fixture checks completed",
                 f"{type(exc).__name__}: {exc}\n"
                 + "".join(traceback.format_exc()[-1500:]))
        finally:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    ok = c.failures == 0
    header = (f"board --check {'OK' if ok else 'FAIL'} — "
              f"{len(c.lines) - sum(1 for ln in c.lines if not ln.startswith('  '))}"
              f" assertion(s), {c.failures} failed")
    return ok, "\n".join([header, *c.lines])
