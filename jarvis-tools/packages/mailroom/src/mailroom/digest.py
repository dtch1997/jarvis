"""``mailroom render`` / ``serve`` — the digest, which is the veto surface.

Lists what was ingested, the route taken per thought, the Todoist drain delta,
unclear items still at the source, and (propose-only) the stale-sweep prune
candidates. Rendered as markdown (``render``, and the daily flare headline) and
as HTML (``serve`` via the lobby hub). Everything derives from the spool +
state; the optional stale sweep is the only live read.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from . import config, spool


def _parse_ts(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        t = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _counts(thoughts: list[dict]) -> dict:
    by_source, by_type, by_action = {}, {}, {}
    routed = 0
    for t in thoughts:
        by_source[t.get("source")] = by_source.get(t.get("source"), 0) + 1
        tri = t.get("triage") or {}
        if tri:
            by_type[tri.get("type", "unclear")] = by_type.get(tri.get("type", "unclear"), 0) + 1
        rt = t.get("route") or {}
        if rt:
            by_action[rt.get("action")] = by_action.get(rt.get("action"), 0) + 1
            if rt.get("action") not in ("unclear", "label-unclear"):
                routed += 1
    return {"by_source": by_source, "by_type": by_type,
            "by_action": by_action, "routed": routed}


def stale_candidates(client, *, stale_days: int, now: datetime) -> list[dict]:
    """Propose-only: curated-project items untouched for > stale_days. Never
    closes anything — digest listing only."""
    out = []
    for name, pid in config.TODOIST_PROJECTS.items():
        try:
            tasks = client.tasks(pid)
        except Exception:
            continue
        for t in tasks:
            ts = _parse_ts(t.get("updated_at") or t.get("added_at") or t.get("created_at"))
            if ts and (now - ts).days > stale_days:
                out.append({"project": name, "content": t.get("content", ""),
                            "days": (now - ts).days})
    out.sort(key=lambda r: -r["days"])
    return out


def digest_headline(*, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    state = spool.load_state()
    r = state.get("route") or {}
    ing = state.get("ingest") or {}
    c = _counts(spool.load_all_thoughts())
    return (f"mailroom: {sum(c['by_source'].values())} thought(s) "
            f"({c['routed']} routed); Inbox {r.get('inbox_before','?')}→"
            f"{r.get('inbox_after','?')}, {ing.get('voice_transcribed',0)} voice")


def is_nonempty_day(*, now: datetime | None = None, hours: int = 24) -> bool:
    """A day is non-empty if any thought was ingested within the last ``hours``."""
    now = now or datetime.now(timezone.utc)
    for t in spool.load_all_thoughts():
        ts = _parse_ts(t.get("ingested_at"))
        if ts and (now - ts).total_seconds() <= hours * 3600:
            return True
    return False


def flare_headline(*, now: datetime | None = None) -> bool:
    """Daily-digest cron hook: flare the headline (``--sev info``) on a non-empty
    day. Returns whether a flare was sent."""
    if not is_nonempty_day(now=now):
        return False
    try:
        import flare
        flare.send(digest_headline(now=now), sev="info", source="mailroom")
        return True
    except Exception:
        return False


def render_markdown(*, now: datetime | None = None, stale=None) -> str:
    now = now or datetime.now(timezone.utc)
    thoughts = spool.load_all_thoughts()
    thoughts.sort(key=lambda t: t.get("ts") or "", reverse=True)
    c = _counts(thoughts)
    state = spool.load_state()
    r = state.get("route") or {}
    total = len(thoughts)
    routed = c["routed"]
    lines = [f"# mailroom digest — {now:%Y-%m-%d %H:%M UTC}", ""]
    lines.append(f"**{total}** thought(s); **{routed}** routed "
                 f"({(routed/total*100) if total else 0:.0f}%). "
                 f"Sources: " + ", ".join(f"{k} {v}" for k, v in sorted(c["by_source"].items())))
    if r:
        lines.append(f"Todoist Inbox drain: **{r.get('inbox_before','?')} → "
                     f"{r.get('inbox_after','?')}** "
                     f"(moved {r.get('todoist_moved',0)}, closed {r.get('todoist_closed',0)}, "
                     f"labeled-unclear {r.get('todoist_labeled',0)}, "
                     f"**completions {r.get('task_completions','?')}**). "
                     f"Model spend ${r.get('est_spend_usd',0):.3f}.")
    lines.append("")
    lines.append("## Routes")
    lines.append("| thought | source | type | route → target |")
    lines.append("|---|---|---|---|")
    for t in thoughts[:200]:
        tri = t.get("triage") or {}
        rt = t.get("route") or {}
        title = (tri.get("title") or (t.get("raw") or "").strip().splitlines()[0:1] or [""])[0] \
            if not tri.get("title") else tri.get("title")
        title = (title or "")[:70].replace("|", "\\|")
        lines.append(f"| {title} | {t.get('source')} | {tri.get('type','-')} | "
                     f"{rt.get('action','-')} → {rt.get('target','-')} |")

    unclear = [t for t in thoughts if (t.get("route") or {}).get("action") in ("unclear", "label-unclear")]
    if unclear:
        lines += ["", f"## Unclear — stayed at source ({len(unclear)})"]
        for t in unclear[:50]:
            lines.append(f"- {(t.get('raw') or '')[:100]}  ({t.get('permalink','')})")

    if stale:
        lines += ["", f"## Stale-sweep prune candidates (propose-only, {len(stale)})"]
        for s in stale[:50]:
            lines.append(f"- [{s['project']}] {s['content'][:80]} — untouched {s['days']}d")

    lines += ["", "## Proposed (not dispatched)",
              "_Auto-dispatch of concierge tasks is propose-only at MVP; none dispatched._"]
    return "\n".join(lines) + "\n"


def render_html(*, now: datetime | None = None, refresh: int = 60, stale=None) -> str:
    md = render_markdown(now=now, stale=stale)
    body = html.escape(md)
    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"{meta}<title>mailroom digest</title>"
        "<style>body{font:14px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:900px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
        "pre{white-space:pre-wrap;word-wrap:break-word}</style></head>"
        f"<body><pre>{body}</pre></body></html>"
    )
