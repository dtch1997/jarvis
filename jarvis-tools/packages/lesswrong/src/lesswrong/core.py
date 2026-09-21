"""LessWrong / ForumMagnum GraphQL client: posts and comments as plain dicts.

Works anonymously against any ForumMagnum-family forum (LessWrong, EA Forum,
Alignment Forum) — the site is a parameter, LessWrong is the default. The
API serves `contents.markdown` directly, so no HTML conversion is needed.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

DEFAULT_SITE = "https://www.lesswrong.com"
USER_AGENT = "lesswrong-dl/0.1 (jarvis research tooling)"
PAGE_SIZE = 200

POST_FIELDS = """
  _id title slug pageUrl postedAt modifiedAt baseScore voteCount
  commentCount wordCount question af tags { name }
  user { username displayName slug }
  coauthors { username displayName slug }
"""

COMMENT_FIELDS = """
  _id parentCommentId topLevelCommentId postedAt baseScore voteCount
  user { username displayName slug }
  contents { markdown }
"""


class ApiError(RuntimeError):
    pass


def gql(query: str, variables: dict | None = None, *, site: str = DEFAULT_SITE,
        retries: int = 3) -> dict:
    """POST one GraphQL query; return the `data` payload or raise ApiError."""
    req = urllib.request.Request(
        site.rstrip("/") + "/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.load(resp)
            break
        except (urllib.error.URLError, TimeoutError) as e:
            status = getattr(e, "code", None)
            if attempt == retries or (status is not None and status < 500 and status != 429):
                raise ApiError(f"GraphQL request failed: {e}") from e
            time.sleep(2**attempt)
    if body.get("errors"):
        raise ApiError("; ".join(e.get("message", str(e)) for e in body["errors"]))
    return body["data"]


def parse_post_ref(ref: str) -> dict:
    """Turn a post URL, _id, or slug into a selector kwargs dict."""
    m = re.search(r"/posts/([A-Za-z0-9]{15,20})(?:/|$)", ref)
    if m:
        return {"_id": m.group(1)}
    if re.fullmatch(r"[A-Za-z0-9]{15,20}", ref):
        return {"_id": ref}
    return {"slug": ref.strip("/").split("/")[-1]}


def get_post(ref: str, *, site: str = DEFAULT_SITE, with_body: bool = True) -> dict:
    """Fetch one post by URL, _id, or slug."""
    sel = parse_post_ref(ref)
    fields = POST_FIELDS + (" contents { markdown }" if with_body else "")
    if "_id" in sel:
        data = gql(
            "query($id: String) { post(input:{selector:{_id:$id}}) { result { %s } } }"
            % fields, {"id": sel["_id"]}, site=site)
        post = data["post"]["result"]
    else:
        data = gql(
            "query($slug: String) { posts(input:{terms:{view:\"slugPost\",slug:$slug,limit:1}})"
            " { results { %s } } }" % fields, {"slug": sel["slug"]}, site=site)
        results = data["posts"]["results"]
        post = results[0] if results else None
    if post is None:
        raise ApiError(f"post not found: {ref}")
    return post


def resolve_user_id(slug: str, *, site: str = DEFAULT_SITE) -> str:
    data = gql(
        "query($slug: String) { user(input:{selector:{slug:$slug}}) { result { _id } } }",
        {"slug": slug}, site=site)
    user = data["user"]["result"]
    if user is None:
        raise ApiError(f"user not found: {slug}")
    return user["_id"]


def list_posts(*, view: str = "new", user: str | None = None,
               after: str | None = None, before: str | None = None,
               limit: int = 50, with_body: bool = False,
               site: str = DEFAULT_SITE) -> list[dict]:
    """List post metadata (JSONL-able dicts), paginating under the hood."""
    terms: dict = {"view": "userPosts" if user else view}
    if user:
        terms["userId"] = resolve_user_id(user, site=site)
    if after:
        terms["after"] = after
    if before:
        terms["before"] = before
    fields = POST_FIELDS + (" contents { markdown }" if with_body else "")
    out: list[dict] = []
    while len(out) < limit:
        chunk = min(PAGE_SIZE, limit - len(out))
        data = gql(
            "query($terms: JSON) { posts(input:{terms:$terms}) { results { %s } } }" % fields,
            {"terms": {**terms, "limit": chunk, "offset": len(out)}}, site=site)
        results = data["posts"]["results"]
        out.extend(results)
        if len(results) < chunk:
            break
    return out


def get_comments(post_ref: str, *, site: str = DEFAULT_SITE) -> list[dict]:
    """Fetch all comments on a post, in thread order with a `depth` key added."""
    post_id = parse_post_ref(post_ref).get("_id") or get_post(
        post_ref, site=site, with_body=False)["_id"]
    raw: list[dict] = []
    while True:
        data = gql(
            "query($terms: JSON) { comments(input:{terms:$terms}) { results { %s } } }"
            % COMMENT_FIELDS,
            {"terms": {"view": "postCommentsNew", "postId": post_id,
                       "limit": PAGE_SIZE, "offset": len(raw)}}, site=site)
        results = data["comments"]["results"]
        raw.extend(results)
        if len(results) < PAGE_SIZE:
            break
    return thread_comments(raw)


def thread_comments(comments: list[dict]) -> list[dict]:
    """Order comments depth-first by thread; annotate each with `depth`."""
    by_parent: dict[str | None, list[dict]] = {}
    ids = {c["_id"] for c in comments}
    for c in comments:
        parent = c.get("parentCommentId")
        # A parent outside the fetched set (e.g. deleted) roots its subtree.
        by_parent.setdefault(parent if parent in ids else None, []).append(c)
    for siblings in by_parent.values():
        siblings.sort(key=lambda c: c.get("postedAt") or "")
    out: list[dict] = []

    def walk(parent: str | None, depth: int) -> None:
        for c in by_parent.get(parent, []):
            c["depth"] = depth
            out.append(c)
            walk(c["_id"], depth + 1)

    walk(None, 0)
    return out
