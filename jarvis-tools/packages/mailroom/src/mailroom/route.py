"""``mailroom route`` — triage untriaged thoughts, then land each on a spine.

Two phases:

1. **triage** — batched ``claude -p`` over thoughts with no triage yet (per-run
   call cap; a batch is one call). Fills ``record["triage"]``.
2. **actuate** — the routing table (spec § Routing). Todoist's hard rule is
   *file, never complete*: task-typed Inbox items are MOVED and stay open;
   close-with-comment is only for non-task captures whose content transferred to
   a better-tracked spine. Zero completions of task-typed items — enforced
   structurally (``close`` is never called on a todo/admin) and asserted.

``route_check`` is the gate hook (offline, no model): ≥ threshold routed, drain
delta recorded, zero task-completions logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import actuators, config, slack, spool, todoist
from .registry import goal_slugs, memory_index_slugs

# route actions that are "non-obvious" enough to warrant a Slack threaded reply
_REPLY_ACTIONS = {"threads-note", "goal-bullet", "papers-task", "flare"}
# actions that count as "routed" for the auto-route %.
_UNROUTED = {"unclear", "label-unclear"}
# a thought older than this can't be time-sensitive anymore — never flare it,
# whatever triage says (backlog drains once mass-flared weeks-old captures).
_URGENT_MAX_AGE_DAYS = 7
# how many urgent titles the batch flare bullets before "+N more"
_URGENT_TITLES_SHOWN = 5


@dataclass
class RouteResult:
    triaged: int = 0
    model_calls: int = 0
    truncated: bool = False
    est_spend_usd: float = 0.0
    routed: int = 0
    unclear: int = 0
    by_type: dict = field(default_factory=dict)
    todoist_moved: int = 0
    todoist_closed: int = 0
    todoist_labeled: int = 0
    todoist_created: int = 0
    task_completions: int = 0  # MUST stay 0
    replies: int = 0
    urgent: list = field(default_factory=list)  # titles of fresh urgent captures
    inbox_before: int | None = None
    inbox_after: int | None = None
    errors: list[str] = field(default_factory=list)

    def report(self) -> str:
        bt = ", ".join(f"{k}:{v}" for k, v in sorted(self.by_type.items()))
        drain = ""
        if self.inbox_before is not None:
            drain = (f"; Inbox {self.inbox_before}→{self.inbox_after} "
                     f"(moved {self.todoist_moved}, closed {self.todoist_closed}, "
                     f"labeled-unclear {self.todoist_labeled}, "
                     f"completions {self.task_completions})")
        return (
            f"route: triaged {self.triaged} ({self.model_calls} call(s), "
            f"${self.est_spend_usd:.3f}), routed {self.routed}, unclear {self.unclear}; "
            f"types [{bt}]; todoist +{self.todoist_created} task(s){drain}"
            + (f"; {len(self.urgent)} urgent" if self.urgent else "")
            + ("  — CALL CAP HIT" if self.truncated else "")
            + (f"; {len(self.errors)} error(s)" if self.errors else "")
        )


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return "-".join(s.split("-")[:6]) or "captured-thought"


def _is_fresh(thought: dict, now: datetime, max_age_days: float) -> bool:
    ts_raw = thought.get("ts")
    if not isinstance(ts_raw, str) or not ts_raw:
        return False
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() <= max_age_days * 86400


# --------------------------------------------------------------------------- #
# phase 1 — triage
# --------------------------------------------------------------------------- #
def _run_triage(thoughts: list[dict], *, runner, model, cfg, res: RouteResult,
                now: datetime) -> None:
    from . import triage as triage_mod
    slugs = memory_index_slugs()
    goals = goal_slugs()
    pending = [t for t in thoughts if not t.get("triage")]
    batches = [pending[i:i + cfg.triage_batch]
               for i in range(0, len(pending), cfg.triage_batch)]
    for batch in batches:
        if res.model_calls >= cfg.max_calls:
            res.truncated = True
            break
        try:
            by_id, cost = triage_mod.triage_batch(batch, slugs, goals,
                                                  runner=runner, model=model)
        except Exception as e:
            res.errors.append(f"triage batch: {e}")
            continue
        res.model_calls += 1
        res.est_spend_usd += cost or config.EST_USD_PER_CALL
        for t in batch:
            tri = by_id.get(t["id"]) or {"type": "unclear", "title": "(untitled)"}
            t["triage"] = tri
            t["triaged_at"] = now.isoformat()
            spool.write_thought(t)
            res.triaged += 1
    if res.truncated:
        try:
            import flare
            flare.send(f"mailroom route hit the {cfg.max_calls}-call cap; "
                       "some thoughts left untriaged", sev="warn", source="mailroom")
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# phase 2 — actuate
# --------------------------------------------------------------------------- #
@dataclass
class _Ctx:
    cfg: config.Config
    note_runner: object
    todoist_client: todoist.TodoistClient | None
    slack_client: slack.SlackClient | None
    arxiv_runner: object
    goals_dir: object
    now: datetime
    res: RouteResult
    dry_todoist: bool = False


def _close_transfer(ctx: _Ctx, thought: dict, dest: str) -> None:
    """Custody transfer: close a NON-task Inbox item with a comment linking its
    new home. Never called for todo/admin (that would be a task completion)."""
    td = thought.get("todoist") or {}
    tid = td.get("task_id")
    if not tid or ctx.dry_todoist or ctx.todoist_client is None:
        ctx.res.todoist_closed += 1
        return
    try:
        ctx.todoist_client.comment(tid, f"mailroom: transferred to {dest}; closing Inbox copy")
        ctx.todoist_client.close(tid)
        ctx.res.todoist_closed += 1
    except Exception as e:
        ctx.res.errors.append(f"close {tid}: {e}")


def _move_file(ctx: _Ctx, thought: dict, project_id: str) -> None:
    """File a task-typed Inbox item into a curated project; STAYS OPEN."""
    td = thought.get("todoist") or {}
    tid = td.get("task_id")
    if not tid or ctx.dry_todoist or ctx.todoist_client is None:
        ctx.res.todoist_moved += 1
        return
    try:
        ctx.todoist_client.move(tid, project_id)
        ctx.todoist_client.comment(tid, "mailroom: filed from Inbox")
        ctx.res.todoist_moved += 1
    except Exception as e:
        ctx.res.errors.append(f"move {tid}: {e}")


def _label_unclear(ctx: _Ctx, thought: dict) -> None:
    td = thought.get("todoist") or {}
    tid = td.get("task_id")
    if not tid or ctx.dry_todoist or ctx.todoist_client is None:
        ctx.res.todoist_labeled += 1
        return
    try:
        ctx.todoist_client.add_label(tid, {"labels": td.get("labels") or []})
        ctx.res.todoist_labeled += 1
    except Exception as e:
        ctx.res.errors.append(f"label {tid}: {e}")


def _create_task(ctx: _Ctx, project_id: str, content: str, description: str) -> None:
    if ctx.dry_todoist or ctx.todoist_client is None:
        ctx.res.todoist_created += 1
        return
    try:
        ctx.todoist_client.create_task(content, project_id=project_id, description=description)
        ctx.res.todoist_created += 1
    except Exception as e:
        ctx.res.errors.append(f"create task: {e}")


def _actuate(thought: dict, ctx: _Ctx) -> dict:
    tri = thought.get("triage") or {}
    ttype = tri.get("type", "unclear")
    source = thought.get("source")
    is_todoist = source == "todoist"
    title = tri.get("title") or (thought.get("raw") or "")[:80]
    action, target = "unclear", source

    # urgent/blocked augmentation — collected here, flared ONCE per run at the
    # end of route() (per-item flares flooded #lab-notes-daniel). Backfill and
    # stale thoughts are never urgent, whatever triage says.
    if (tri.get("urgency") == "high" and not thought.get("backfill")
            and _is_fresh(thought, ctx.now, _URGENT_MAX_AGE_DAYS)):
        ctx.res.urgent.append(title)

    if ttype == "thread-note":
        slug = (tri.get("candidate_slugs") or [None])[0] or _slugify(title)
        actuators.land_note(slug, thought, note_runner=ctx.note_runner)
        action, target = "threads-note", slug
        if is_todoist:
            _close_transfer(ctx, thought, f"threads note '{slug}'")

    elif ttype == "goal-signal" and tri.get("goal") in goal_slugs():
        goal = tri["goal"]
        actuators.append_goal_bullet(goal, title, now=ctx.now, goals_dir=ctx.goals_dir)
        action, target = "goal-bullet", goal
        if is_todoist:
            _close_transfer(ctx, thought, f"goal '{goal}'")

    elif ttype in ("research-idea", "goal-signal"):
        # no valid goal home → seed a candidate thread
        slug = (tri.get("candidate_slugs") or [None])[0] or _slugify(title)
        actuators.land_note(slug, thought, note_runner=ctx.note_runner, status="parked")
        action, target = "threads-note", slug
        if is_todoist:
            _close_transfer(ctx, thought, f"candidate thread '{slug}'")

    elif ttype == "paper":
        pid = config.TODOIST_PROJECTS[config.PAPERS_PROJECT]
        _create_task(ctx, pid, title, thought.get("raw", "") + "\n" + thought.get("permalink", ""))
        if tri.get("arxiv_id"):
            ctx.arxiv_runner(tri["arxiv_id"])
        action, target = "papers-task", config.PAPERS_PROJECT
        if is_todoist:
            _close_transfer(ctx, thought, "Papers to read")

    elif ttype in ("todo", "admin"):
        pid = todoist.resolve_project(tri.get("project")) \
            or config.TODOIST_PROJECTS["Focus Areas"]
        pname = todoist.project_name(pid)
        if is_todoist:
            _move_file(ctx, thought, pid)   # STAYS OPEN — file, never complete
            action = "todoist-move"
        else:
            _create_task(ctx, pid, title, thought.get("raw", "") + "\n" + thought.get("permalink", ""))
            action = "todoist-task"
        target = pname

    else:  # unclear
        if is_todoist:
            _label_unclear(ctx, thought)
            action, target = "label-unclear", "Inbox"
        else:
            action, target = "unclear", source

    return {"action": action, "target": target, "at": ctx.now.isoformat()}


def _maybe_reply(thought: dict, route: dict, ctx: _Ctx) -> None:
    """reply_on_route: a short threaded reply on *newly-ingested* Slack messages
    (never on the backfill) when the route was non-obvious."""
    if not ctx.cfg.reply_on_route or ctx.slack_client is None:
        return
    if thought.get("source") not in ("slack", "voice") or thought.get("backfill"):
        return
    if route["action"] not in _REPLY_ACTIONS:
        return
    sl = thought.get("slack") or {}
    if not sl.get("channel") or not sl.get("ts"):
        return
    msg = {"threads-note": f"→ landed on threads note `{route['target']}`",
           "goal-bullet": f"→ bulleted onto goal `{route['target']}`",
           "papers-task": "→ filed to Todoist ‘Papers to read’",
           "flare": "→ flared as urgent"}.get(route["action"], "→ routed")
    try:
        ctx.slack_client.post_reply(sl["channel"], sl["ts"], f"mailroom {msg}")
        ctx.res.replies += 1
    except Exception as e:
        ctx.res.errors.append(f"reply {thought['id']}: {e}")


# --------------------------------------------------------------------------- #
# public entry points
# --------------------------------------------------------------------------- #
def route(*, runner=None, model: str = config.MODEL,
          todoist_client: todoist.TodoistClient | None = None,
          slack_client: slack.SlackClient | None = None,
          note_runner=actuators.default_note_runner,
          arxiv_runner=actuators.default_arxiv_runner,
          goals_dir=None, dry_todoist: bool = False,
          now: datetime | None = None) -> RouteResult:
    now = now or datetime.now(timezone.utc)
    config.ensure_spool()
    cfg = config.load_config()
    res = RouteResult()

    if runner is None:
        from .triage import default_runner as runner  # noqa

    thoughts = spool.load_all_thoughts()
    _run_triage(thoughts, runner=runner, model=model, cfg=cfg, res=res, now=now)

    # drain baseline
    if todoist_client is None and not dry_todoist:
        todoist_client = todoist.TodoistClient()
    if todoist_client is not None:
        try:
            res.inbox_before = len(todoist_client.inbox_tasks())
        except Exception as e:
            res.errors.append(f"inbox count (before): {e}")

    ctx = _Ctx(cfg=cfg, note_runner=note_runner, todoist_client=todoist_client,
               slack_client=slack_client, arxiv_runner=arxiv_runner,
               goals_dir=goals_dir, now=now, res=res, dry_todoist=dry_todoist)

    for thought in spool.load_all_thoughts():
        if not thought.get("triage"):
            continue
        if thought.get("route"):  # already actuated — idempotent
            res.by_type[thought["triage"].get("type", "unclear")] = \
                res.by_type.get(thought["triage"].get("type", "unclear"), 0) + 1
            if thought["route"]["action"] not in _UNROUTED:
                res.routed += 1
            else:
                res.unclear += 1
            continue
        route_rec = _actuate(thought, ctx)
        thought["route"] = route_rec
        spool.write_thought(thought)
        ttype = thought["triage"].get("type", "unclear")
        res.by_type[ttype] = res.by_type.get(ttype, 0) + 1
        if route_rec["action"] not in _UNROUTED:
            res.routed += 1
        else:
            res.unclear += 1
        _maybe_reply(thought, route_rec, ctx)

    if todoist_client is not None:
        try:
            res.inbox_after = len(todoist_client.inbox_tasks())
        except Exception as e:
            res.errors.append(f"inbox count (after): {e}")

    # ONE flare per run covering every fresh urgent capture — never per item.
    # Format per Daniel: concise headline, one bullet per point.
    if res.urgent:
        shown = res.urgent[:_URGENT_TITLES_SHOWN]
        extra = len(res.urgent) - len(shown)
        n = len(res.urgent)
        lines = [f"mailroom: {n} urgent capture{'s' if n != 1 else ''}"]
        lines += [f"• {t}" for t in shown]
        if extra:
            lines.append(f"+{extra} more — see the mailroom digest")
        actuators.send_flare("\n".join(lines), sev="warn")

    st = spool.load_state()
    st["last_route"] = now.isoformat()
    st["route"] = {
        "triaged": res.triaged, "model_calls": res.model_calls,
        "est_spend_usd": round(res.est_spend_usd, 4),
        "routed": res.routed, "unclear": res.unclear, "by_type": res.by_type,
        "todoist_moved": res.todoist_moved, "todoist_closed": res.todoist_closed,
        "todoist_labeled": res.todoist_labeled, "todoist_created": res.todoist_created,
        "task_completions": res.task_completions, "replies": res.replies,
        "urgent": len(res.urgent),
        "inbox_before": res.inbox_before, "inbox_after": res.inbox_after,
        "truncated": res.truncated,
    }
    spool.write_state(st)
    return res


def route_check(*, now: datetime | None = None) -> tuple[bool, str]:
    """Gate: ≥ threshold of thoughts routed, drain delta recorded, zero
    task-completions logged. Offline (spool + state only)."""
    cfg = config.load_config()
    thoughts = spool.load_all_thoughts()
    if not thoughts:
        return False, "route --check: no thoughts in spool (run ingest first)"
    untriaged = [t for t in thoughts if not t.get("triage")]
    if untriaged:
        return False, f"route --check FAIL: {len(untriaged)} thought(s) still untriaged"
    unrouted = [t for t in thoughts if not t.get("route")]
    if unrouted:
        return False, f"route --check FAIL: {len(unrouted)} thought(s) not yet routed"

    total = len(thoughts)
    routed = sum(1 for t in thoughts if (t.get("route") or {}).get("action") not in _UNROUTED)
    ratio = routed / total
    state = spool.load_state()
    r = state.get("route") or {}
    if "inbox_before" not in r or r.get("inbox_before") is None:
        return False, "route --check FAIL: Todoist drain delta not recorded"
    completions = r.get("task_completions", -1)
    if completions != 0:
        return False, f"route --check FAIL: {completions} task-completion(s) logged (must be 0)"
    if ratio < cfg.route_threshold:
        return False, (f"route --check FAIL: {routed}/{total} routed "
                       f"({ratio*100:.0f}% < {cfg.route_threshold*100:.0f}%)")
    return True, (f"route --check OK: {routed}/{total} routed ({ratio*100:.0f}%), "
                  f"Inbox {r.get('inbox_before')}→{r.get('inbox_after')}, "
                  f"0 task-completions")
