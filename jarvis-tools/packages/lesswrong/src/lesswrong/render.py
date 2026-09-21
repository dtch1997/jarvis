"""Render posts and comment threads as agent-legible markdown."""

from __future__ import annotations


def _author(entity: dict) -> str:
    user = entity.get("user") or {}
    names = [user.get("displayName") or user.get("username") or "[deleted]"]
    names += [c.get("displayName") or c.get("username") or "?"
              for c in entity.get("coauthors") or []]
    return ", ".join(names)


def _date(iso: str | None) -> str:
    return (iso or "")[:10]


def render_post(post: dict, comments: list[dict] | None = None) -> str:
    lines = [
        "---",
        f"title: {json_str(post.get('title'))}",
        f"author: {json_str(_author(post))}",
        f"date: {_date(post.get('postedAt'))}",
        f"karma: {post.get('baseScore')}",
        f"votes: {post.get('voteCount')}",
        f"comments: {post.get('commentCount')}",
        f"words: {post.get('wordCount')}",
        f"url: {post.get('pageUrl')}",
        f"id: {post.get('_id')}",
    ]
    tags = [t["name"] for t in post.get("tags") or []]
    if tags:
        lines.append("tags: [" + ", ".join(tags) + "]")
    lines += ["---", "", f"# {post.get('title')}", ""]
    body = (post.get("contents") or {}).get("markdown")
    lines.append(body if body else "*[no body available]*")
    if comments is not None:
        lines += ["", "---", "", f"## Comments ({len(comments)})", ""]
        lines.append(render_comments(comments))
    return "\n".join(lines).rstrip() + "\n"


def render_comments(comments: list[dict]) -> str:
    """Thread-ordered comments; depth shown by nested-quote markers."""
    blocks = []
    for c in comments:
        depth = c.get("depth", 0)
        header = (f"{'#' * min(3 + depth, 6)} {_author(c)} "
                  f"· {c.get('baseScore')} karma · {_date(c.get('postedAt'))} "
                  f"· depth {depth}")
        body = (c.get("contents") or {}).get("markdown") or "*[deleted]*"
        blocks.append(f"{header}\n\n{body}\n")
    return "\n".join(blocks)


def json_str(value: object) -> str:
    """YAML-safe scalar: quote strings that could confuse a YAML parser."""
    import json

    return json.dumps(value) if isinstance(value, str) else str(value)
