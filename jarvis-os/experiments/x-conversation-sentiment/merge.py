#!/usr/bin/env python3
"""Union every download directory for one post into data/<id>/all_posts.jsonl.

Replies come from several query styles (conversation_id, in_reply_to_tweet_id,
to:author, full-archive), each in its own data/<id>-<suffix>/ dir; quotes from
the main dir. Dedupes on id, keeps the first copy, tags each row with `kind`
(reply|quote|thread) and `depth` (1 = direct reply to root, 2 = deeper).

    ./merge.py [tweet-id]
"""
import json
import sys
from pathlib import Path


def rows(p: Path):
    if p.exists():
        for line in p.read_text().split("\n"):
            if line.strip():
                yield json.loads(line)


def main() -> None:
    root_id = sys.argv[1] if len(sys.argv) > 1 else "2097476196791709843"
    data = Path(__file__).parent / "data"
    main_dir = data / root_id
    root = json.loads((main_dir / "root.json").read_text())
    author = root["data"]["author_id"]

    users: dict[str, dict] = {}
    posts: dict[str, dict] = {}
    sources: dict[str, list[str]] = {}
    for d in sorted(data.glob(f"{root_id}*")):
        if not d.is_dir():
            continue
        for u in rows(d / "users.jsonl"):
            users.setdefault(u["id"], u)
        for kind, fname in [("reply", "replies.jsonl"), ("quote", "quotes.jsonl")]:
            for t in rows(d / fname):
                if t["id"] == root_id or t.get("conversation_id") != root_id and kind == "reply":
                    continue
                sources.setdefault(t["id"], []).append(d.name.replace(root_id, "") or "-conv")
                if t["id"] in posts:
                    continue
                parent = next((r["id"] for r in t.get("referenced_tweets", []) if r["type"] == "replied_to"), "")
                t["kind"] = "thread" if (kind == "reply" and t["author_id"] == author) else kind
                t["depth"] = (1 if parent == root_id else 2) if kind == "reply" else 0
                t["parent_id"] = parent
                t["full_text"] = (t.get("note_tweet") or {}).get("text") or t.get("text", "")
                u = users.get(t["author_id"], {})
                t["username"] = u.get("username", "")
                t["followers"] = u.get("public_metrics", {}).get("followers_count")
                posts[t["id"]] = t
    for pid, t in posts.items():
        t["sources"] = sorted(set(sources[pid]))

    out = main_dir / "all_posts.jsonl"
    with out.open("w") as f:
        for t in sorted(posts.values(), key=lambda t: t["created_at"]):
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    with (main_dir / "all_users.jsonl").open("w") as f:
        for u in users.values():
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter((t["kind"], t["depth"]) for t in posts.values())
    print(f"wrote {len(posts)} posts to {out}: {dict(c)}; {len(users)} users")


if __name__ == "__main__":
    main()
