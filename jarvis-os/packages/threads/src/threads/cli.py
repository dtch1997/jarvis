"""``threads scan|weave|serve|render|status|note|pickup`` — the bottom-up
activity spine, plus the deliberate push channel (``note``/``pickup``).

``scan``/``weave`` take ``--check`` gate hooks that are cheap and offline (no
model calls): they exit 0 iff the spool is complete and consistent.
"""

from __future__ import annotations

import sys
import time

from . import config


def _cmd_scan(args) -> int:
    from .scan import scan, scan_check
    if args.check:
        ok, report = scan_check(days=args.days)
        print(report)
        return 0 if ok else 1
    res = scan(days=args.days, max_calls=args.max_calls, all_=args.all)
    print(res.report())
    for e in res.errors[:20]:
        print(f"  ! {e}", file=sys.stderr)
    return 0


def _cmd_weave(args) -> int:
    from .weave import weave, weave_check
    if args.check:
        ok, report = weave_check()
        print(report)
        return 0 if ok else 1
    res = weave(cluster=not args.no_cluster, vault=not args.no_vault)
    print(res.report())
    return 0


def _cmd_launch(args) -> int:
    from .launch import accept, launch_check, process_intent, _offline_runner
    if args.check:
        ok, report = launch_check()
        print(report)
        return 0 if ok else 1
    started = time.perf_counter()
    try:
        rec = accept(" ".join(args.text),
                     mode="copilot" if args.copilot else "full-auto",
                     slug=args.slug, dry_run=args.dry_run,
                     enqueue=not args.dry_run)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    latency = (time.perf_counter() - started) * 1000
    print(f"accepted {rec['id']} in {latency:.2f} ms "
          f"(mode={rec['mode']}) — routing async onto the thread")
    if args.dry_run:
        # route + stamp inline, offline (no model, no executor spawn)
        rec = process_intent(rec["id"], runner=_offline_runner)
        print(f"dry-run routed → slug '{rec.get('resolved_slug')}' "
              f"(handle {rec.get('executor_handle')})")
    return 0


def _view_params(args):
    from .dashboard import ViewParams
    return ViewParams(
        sort=args.sort,
        filter_active_days=args.filter_active_days,
        dormant_only=args.filter_dormant,
        q=args.filter_search or "",
    ).normalized()


def _cmd_render(args) -> int:
    from .dashboard import render_markdown
    print(render_markdown(params=_view_params(args)))
    return 0


def _cmd_vault(args) -> int:
    from .vault import write_vault
    res = write_vault()
    print(res.report())
    return 0


def _cmd_note(args) -> int:
    from .note import add_note
    from .registry import load_registry
    body = " ".join(args.text)
    if body in ("", "-"):
        body = sys.stdin.read()
    try:
        path = add_note(args.slug, body, title=args.title, status=args.status)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    known = load_registry().has(args.slug)
    print(f"noted → {path}")
    if not known:
        print(f"  '{args.slug}' is not a memory-stub slug yet — the note seeds a "
              "candidate thread (promotion = memory-consolidate or Daniel).")
    print(f"  pick it back up with: threads pickup {args.slug}")
    return 0


def _cmd_pickup(args) -> int:
    from .dashboard import render_pickup
    print(render_pickup(args.slug))
    return 0


def _cmd_status(args) -> int:
    from .dashboard import build
    from .scan import scan_check
    from .weave import weave_check
    dash = build()
    dormant = [t.slug for t in dash.threads if t.dormant]
    print(f"threads: {len(dash.threads)} active, {len(dash.unfiled)} unfiled, "
          f"{len(dash.candidates)} candidate(s); match rate "
          f"{dash.match_rate * 100:.0f}%")
    if dormant:
        print(f"  dormant (>{dash.dormant_days}d): {', '.join(dormant)}")
    s_ok, _ = scan_check(days=config.DEFAULT_LOOKBACK_DAYS)
    w_ok, _ = weave_check()
    print(f"  scan --check: {'OK' if s_ok else 'FAIL'} · "
          f"weave --check: {'OK' if w_ok else 'FAIL'}")
    return 0


def _cmd_serve(args) -> int:
    from .server import serve
    srv = serve(interval=args.interval, port=args.port, tunnel=not args.no_tunnel)
    # flush=True so the URL lands in the log immediately under `tmux ... > log`
    # (the process then blocks in the keep-alive loop and never flushes on exit).
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


def _add_view_flags(sp) -> None:
    from .dashboard import SORT_KEYS
    sp.add_argument("--sort", choices=SORT_KEYS, default="relevance",
                    help="thread sort key (default: relevance)")
    sp.add_argument("--filter-active-days", type=int, default=None,
                    help="only threads active within N days")
    sp.add_argument("--filter-dormant", action="store_true",
                    help="only dormant threads")
    sp.add_argument("--filter-search", default="",
                    help="text search over slug + latest title")


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="threads", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan", help="summarize new/grown sessions")
    sp.add_argument("--days", type=int, default=config.DEFAULT_LOOKBACK_DAYS,
                    help=f"lookback window (default: {config.DEFAULT_LOOKBACK_DAYS})")
    sp.add_argument("--max-calls", type=int, default=config.DEFAULT_MAX_CALLS,
                    help=f"per-run model-call cap (default: {config.DEFAULT_MAX_CALLS})")
    sp.add_argument("--all", action="store_true",
                    help="lift the call cap (backfill)")
    sp.add_argument("--check", action="store_true",
                    help="offline gate: spool covers the window and is a no-op re-scan")

    wp = sub.add_parser("weave", help="assign summaries to threads")
    wp.add_argument("--no-cluster", action="store_true",
                    help="skip the candidate-thread clustering model call")
    wp.add_argument("--no-vault", action="store_true",
                    help="skip regenerating the Obsidian vault mirror after weave")
    wp.add_argument("--check", action="store_true",
                    help="offline gate: coverage + deterministic-match-rate thresholds")

    rp = sub.add_parser("render", help="print the dashboard as a markdown digest")
    _add_view_flags(rp)
    sub.add_parser("status", help="one-line activity + gate summary")

    sub.add_parser("vault", help="regenerate the Obsidian-compatible vault mirror")

    np = sub.add_parser(
        "note", help="push a durable context-dump onto a thread",
        description="Park what you're holding before moving on: "
                    "threads note <slug> \"...\" — or pipe a longer markdown "
                    "body via stdin (threads note <slug> - <<'EOF' ... EOF). "
                    "cwd/branch/session are captured automatically.")
    np.add_argument("slug", help="memory-stub slug (or a new kebab-case name "
                                 "to seed a candidate thread)")
    np.add_argument("text", nargs="*",
                    help="note body; empty or '-' reads markdown from stdin")
    np.add_argument("--title", help="one-line title (default: first line of body)")
    np.add_argument("--status", choices=["parked", "blocked", "ongoing", "done"],
                    help="how this thread stands as you leave it")

    pp = sub.add_parser("pickup",
                        help="print a thread's context-pack (notes + recent "
                             "sessions) for resuming work")
    pp.add_argument("slug")

    lp = sub.add_parser(
        "launch", help="durably accept an intent and launch its thread",
        description="Send an intent to a thread: threads launch \"<text>\" "
                    "[--copilot] [--slug <slug>]. Acceptance is durable and "
                    "<100ms; routing + spawning happen async onto the thread.")
    lp.add_argument("text", nargs="*", help="the intent text")
    lp.add_argument("--copilot", action="store_true",
                    help="spawn an interactive tmux copilot (default: full-auto)")
    lp.add_argument("--slug", help="pin the destination thread slug")
    lp.add_argument("--dry-run", action="store_true",
                    help="route + stamp offline without spawning a real executor")
    lp.add_argument("--check", action="store_true",
                    help="offline gate: accept-latency <100ms + intent-spool consistency")

    sv = sub.add_parser("serve", help="serve the dashboard through the lobby hub")
    sv.add_argument("--port", type=int, help="local port (default: free port)")
    sv.add_argument("--interval", type=int, default=60,
                    help="re-render interval in seconds (default: 60)")
    sv.add_argument("--no-tunnel", action="store_true",
                    help="serve locally only, skip the lobby hub")

    args = p.parse_args(argv)
    return {
        "scan": _cmd_scan, "weave": _cmd_weave, "render": _cmd_render,
        "status": _cmd_status, "serve": _cmd_serve, "vault": _cmd_vault,
        "note": _cmd_note, "pickup": _cmd_pickup, "launch": _cmd_launch,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
