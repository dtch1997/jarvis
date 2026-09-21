"""`lw` — download LessWrong posts/comments as markdown or JSONL.

Examples:
    lw get https://www.lesswrong.com/posts/iKm2FhpWkuuBojm82/why-i-left-google-deepmind
    lw get why-i-left-google-deepmind --comments -o post.md
    lw list --user turntrout --limit 20
    lw list --view top --after 2026-01-01 --json
    lw comments iKm2FhpWkuuBojm82
    lw --site https://forum.effectivealtruism.org get <ref>
"""

from __future__ import annotations

import argparse
import json
import sys

from . import core, render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lw", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", default=core.DEFAULT_SITE,
                        help="ForumMagnum site base URL (default: LessWrong)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="download one post as markdown")
    p_get.add_argument("ref", help="post URL, _id, or slug")
    p_get.add_argument("--comments", action="store_true",
                       help="append the full comment thread")
    p_get.add_argument("--json", action="store_true", help="raw JSON instead of markdown")
    p_get.add_argument("-o", "--output", help="write to file instead of stdout")

    p_list = sub.add_parser("list", help="list post metadata as JSONL")
    p_list.add_argument("--view", default="new", choices=["new", "top", "old"],
                        help="sort order (ignored with --user)")
    p_list.add_argument("--user", help="filter to a user's posts (by slug)")
    p_list.add_argument("--after", help="ISO date lower bound, e.g. 2026-01-01")
    p_list.add_argument("--before", help="ISO date upper bound")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--body", action="store_true", help="include post bodies")

    p_com = sub.add_parser("comments", help="download a post's comment thread")
    p_com.add_argument("ref", help="post URL, _id, or slug")
    p_com.add_argument("--json", action="store_true", help="JSONL instead of markdown")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "get":
            post = core.get_post(args.ref, site=args.site)
            comments = core.get_comments(post["_id"], site=args.site) if args.comments else None
            if args.json:
                out = json.dumps({"post": post, "comments": comments}, indent=1)
            else:
                out = render.render_post(post, comments)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(out)
                print(f"wrote {args.output}", file=sys.stderr)
            else:
                print(out, end="")
        elif args.cmd == "list":
            posts = core.list_posts(view=args.view, user=args.user, after=args.after,
                                    before=args.before, limit=args.limit,
                                    with_body=args.body, site=args.site)
            for p in posts:
                print(json.dumps(p))
        elif args.cmd == "comments":
            comments = core.get_comments(args.ref, site=args.site)
            if args.json:
                for c in comments:
                    print(json.dumps(c))
            else:
                print(render.render_comments(comments), end="")
    except core.ApiError as e:
        print(f"lw: {e}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Downstream consumer (head, etc.) closed the pipe — not an error.
        sys.stderr.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
