"""``mailroom ingest|route|render|serve|status`` — thought-capture pipeline.

``ingest``/``route`` take ``--check`` gate hooks: ``ingest --check`` verifies
every source item since backfill start has a record (a re-run is a no-op, no
model calls); ``route --check`` verifies ≥ threshold routed, the drain delta is
recorded, and zero task-completions were logged.
"""

from __future__ import annotations

import sys
import time


def _cmd_ingest(args) -> int:
    from .ingest import ingest, ingest_check
    if args.check:
        ok, report = ingest_check()
        print(report)
        return 0 if ok else 1
    res = ingest(backfill=args.backfill, do_slack=not args.no_slack,
                 do_todoist=not args.no_todoist, react=not args.no_react)
    print(res.report())
    for e in res.errors[:20]:
        print(f"  ! {e}", file=sys.stderr)
    return 0


def _cmd_route(args) -> int:
    from .route import route, route_check
    if args.check:
        ok, report = route_check()
        print(report)
        return 0 if ok else 1
    res = route(dry_todoist=args.dry_todoist)
    print(res.report())
    for e in res.errors[:20]:
        print(f"  ! {e}", file=sys.stderr)
    return 0


def _cmd_render(args) -> int:
    from . import config, digest
    stale = None
    if not args.no_stale:
        try:
            from datetime import datetime, timezone
            from .todoist import TodoistClient
            stale = digest.stale_candidates(
                TodoistClient(), stale_days=config.load_config().stale_days,
                now=datetime.now(timezone.utc))
        except Exception:
            stale = None
    print(digest.render_markdown(stale=stale))
    if args.flare:
        if digest.flare_headline():
            print("(flared digest headline --sev info)", file=sys.stderr)
    return 0


def _cmd_status(args) -> int:
    from . import spool
    from .digest import digest_headline
    from .route import route_check
    from .ingest import ingest_check  # noqa: F401 (imported for symmetry)
    state = spool.load_state()
    thoughts = spool.load_all_thoughts()
    triaged = sum(1 for t in thoughts if t.get("triage"))
    routed = sum(1 for t in thoughts if (t.get("route") or {}).get("action")
                 not in (None, "unclear", "label-unclear"))
    print(f"mailroom: {len(thoughts)} thought(s), {triaged} triaged, {routed} routed")
    print(f"  {digest_headline()}")
    r_ok, r_msg = route_check()
    print(f"  route --check: {'OK' if r_ok else 'FAIL'} — {r_msg.splitlines()[0]}")
    print(f"  last ingest: {state.get('last_ingest','never')} · "
          f"last route: {state.get('last_route','never')}")
    return 0


def _cmd_voicedoc(args) -> int:
    from . import config
    from .voicedoc import run_once, watch
    if not config.load_config().voicedoc.enabled:
        print("voicedoc: disabled ([voicedoc] enabled = false in config.toml)")
        return 0
    if args.watch:
        watch(interval=args.interval)
        return 0
    records = run_once()
    if not records:
        print("voicedoc: nothing new")
        return 0
    fails = 0
    for r in records:
        status = r.get("error") or r.get("doc_url") or "ok"
        fails += 1 if r.get("error") else 0
        print(f"voicedoc: {r['id']} → {status}")
    return 1 if fails else 0


def _cmd_serve(args) -> int:
    from .server import serve
    srv = serve(interval=args.interval, port=args.port, tunnel=not args.no_tunnel)
    print(f"local:  {srv.local_url}", flush=True)
    if srv.url != srv.local_url:
        print(f"PUBLIC: {srv.url}", flush=True)
    print("serving in the background; Ctrl-C here to stop.", flush=True)
    try:
        while srv.alive:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        srv.stop()
        print("\nstopped.")
    return 0


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="mailroom", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ip = sub.add_parser("ingest", help="pull captures from Slack + Todoist into the spool")
    ip.add_argument("--backfill", action="store_true",
                    help="pull the full backfill window (reactions only, no replies)")
    ip.add_argument("--no-slack", action="store_true", help="skip the Slack leg")
    ip.add_argument("--no-todoist", action="store_true", help="skip the Todoist leg")
    ip.add_argument("--no-react", action="store_true", help="skip ✅ reactions")
    ip.add_argument("--check", action="store_true",
                    help="gate: every source item has a record (no-op re-run, no model)")

    rp = sub.add_parser("route", help="triage untriaged thoughts, then land each on a spine")
    rp.add_argument("--dry-todoist", action="store_true",
                    help="do not mutate Todoist (count intended actions only)")
    rp.add_argument("--check", action="store_true",
                    help="gate: ≥ threshold routed, drain delta recorded, 0 task-completions")

    dp = sub.add_parser("render", help="print the digest (veto surface) as markdown")
    dp.add_argument("--no-stale", action="store_true", help="skip the live stale sweep")
    dp.add_argument("--flare", action="store_true",
                    help="flare the headline (--sev info) on a non-empty day (daily cron)")

    sub.add_parser("status", help="one-line pipeline + gate summary")

    vp = sub.add_parser("voicedoc",
                        help="voice note → work-Drive Google Doc + Slack draft")
    vp.add_argument("--watch", action="store_true",
                    help="poll forever (the tmux daemon mode)")
    vp.add_argument("--interval", type=int,
                    help="override [voicedoc] poll_seconds for --watch")

    sv = sub.add_parser("serve", help="serve the digest through the lobby hub")
    sv.add_argument("--port", type=int, help="local port (default: free port)")
    sv.add_argument("--interval", type=int, default=60, help="re-render interval (s)")
    sv.add_argument("--no-tunnel", action="store_true", help="serve locally only")

    args = p.parse_args(argv)
    return {
        "ingest": _cmd_ingest, "route": _cmd_route, "render": _cmd_render,
        "status": _cmd_status, "serve": _cmd_serve, "voicedoc": _cmd_voicedoc,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
