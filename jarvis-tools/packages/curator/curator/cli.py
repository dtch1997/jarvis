"""curator CLI: add / ls / serve / export over a ledger directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import STATUSES, Ledger


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="curator", description=__doc__)
    p.add_argument("--ledger", default=None,
                   help="ledger directory (default ./gallery or $CURATOR_LEDGER)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("add", help="add a card from an existing figure file")
    ap.add_argument("--figure", required=True, help="path to the plot image")
    ap.add_argument("--claim", required=True, help="what this figure demonstrates")
    ap.add_argument("--notes", default="")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--data", default=None, help="data file(s) behind the plot, comma-separated")

    lp = sub.add_parser("ls", help="list cards")
    lp.add_argument("--status", choices=STATUSES, default=None)

    sp = sub.add_parser("serve", help="serve the gallery (detached) and print the URL")
    sp.add_argument("--port", type=int, default=None)
    sp.add_argument("--no-tunnel", action="store_true", help="skip the lobby hub; local URL only")
    sp.add_argument("--name", default=None, help="name on the lobby hub index")

    ep = sub.add_parser("export", help="write a markdown skeleton of the kept cards")
    ep.add_argument("-o", "--out", default=None, help="output path (default: stdout)")

    args = p.parse_args(argv)
    ledger = Ledger(args.ledger)

    if args.cmd == "add":
        card = ledger.add(
            args.figure,
            args.claim,
            notes=args.notes,
            tags=[t.strip() for t in args.tags.split(",") if t.strip()],
            data=[d.strip() for d in args.data.split(",")] if args.data else None,
        )
        print(f"{card.id}  {card.figure}")
        return 0

    if args.cmd == "ls":
        cards = ledger.cards()
        if args.status:
            cards = [c for c in cards if c.status == args.status]
        if not cards:
            print(f"no cards in {ledger.root}", file=sys.stderr)
            return 1
        for c in cards:
            claim = c.claim if len(c.claim) <= 80 else c.claim[:77] + "..."
            tags = f" [{','.join(c.tags)}]" if c.tags else ""
            print(f"{c.id}  {c.status:9}  {claim}{tags}")
        return 0

    if args.cmd == "serve":
        from .server import serve

        viewer = serve(ledger.root, name=args.name, port=args.port,
                       tunnel=not args.no_tunnel)
        print(viewer.url)
        if viewer.url != viewer.local_url:
            print(f"local: {viewer.local_url}", file=sys.stderr)
        print(f"pid: {viewer.http_pid} (kill to stop)", file=sys.stderr)
        return 0

    if args.cmd == "export":
        md = ledger.export_markdown()
        if args.out:
            Path(args.out).write_text(md)
            print(args.out)
        else:
            print(md)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
