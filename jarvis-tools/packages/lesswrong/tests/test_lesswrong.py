"""Offline tests: ref parsing, comment threading, markdown rendering."""

from lesswrong import parse_post_ref, render_post, thread_comments


def test_parse_post_ref_url():
    ref = "https://www.lesswrong.com/posts/iKm2FhpWkuuBojm82/why-i-left-google-deepmind"
    assert parse_post_ref(ref) == {"_id": "iKm2FhpWkuuBojm82"}


def test_parse_post_ref_url_no_slug():
    assert parse_post_ref("https://www.lesswrong.com/posts/iKm2FhpWkuuBojm82") == {
        "_id": "iKm2FhpWkuuBojm82"
    }


def test_parse_post_ref_bare_id():
    assert parse_post_ref("iKm2FhpWkuuBojm82") == {"_id": "iKm2FhpWkuuBojm82"}


def test_parse_post_ref_slug():
    assert parse_post_ref("why-i-left-google-deepmind") == {
        "slug": "why-i-left-google-deepmind"
    }


def _c(cid, parent, at):
    return {
        "_id": cid,
        "parentCommentId": parent,
        "postedAt": at,
        "baseScore": 1,
        "user": {"displayName": cid},
        "contents": {"markdown": f"body {cid}"},
    }


def test_thread_comments_orders_depth_first():
    # b replies to a; c is a later top-level comment
    threaded = thread_comments([
        _c("c", None, "2026-01-03"),
        _c("a", None, "2026-01-01"),
        _c("b", "a", "2026-01-02"),
    ])
    assert [(c["_id"], c["depth"]) for c in threaded] == [
        ("a", 0), ("b", 1), ("c", 0)]


def test_thread_comments_orphan_parent_becomes_root():
    threaded = thread_comments([_c("x", "gone-parent", "2026-01-01")])
    assert [(c["_id"], c["depth"]) for c in threaded] == [("x", 0)]


def test_render_post_frontmatter_and_comments():
    post = {
        "_id": "abc",
        "title": "A: colon title",
        "postedAt": "2026-01-01T00:00:00Z",
        "baseScore": 10,
        "voteCount": 5,
        "commentCount": 1,
        "wordCount": 2,
        "pageUrl": "https://www.lesswrong.com/posts/abc/x",
        "user": {"displayName": "Alice"},
        "tags": [{"name": "AI"}],
        "contents": {"markdown": "Hello world"},
    }
    comments = thread_comments([_c("a", None, "2026-01-01")])
    out = render_post(post, comments)
    assert out.startswith("---\n")
    assert 'title: "A: colon title"' in out
    assert "karma: 10" in out
    assert "tags: [AI]" in out
    assert "Hello world" in out
    assert "## Comments (1)" in out
    assert "body a" in out


def test_render_post_no_comments_section_when_none():
    post = {"title": "t", "user": None, "contents": {"markdown": "x"}}
    assert "## Comments" not in render_post(post)
