# lesswrong

Download LessWrong posts and comments via the public GraphQL API
(`https://www.lesswrong.com/graphql`), as agent-legible markdown or JSONL.
Stdlib only — the API serves `contents.markdown` directly, so there is no
HTML conversion step. Works against any ForumMagnum-family forum
(LessWrong, EA Forum, Alignment Forum) via `--site`.

## CLI

```bash
# one post → markdown with frontmatter (title, author, karma, url, …)
lw get https://www.lesswrong.com/posts/iKm2FhpWkuuBojm82/why-i-left-google-deepmind
lw get why-i-left-google-deepmind --comments -o post.md   # slug works too

# post metadata → JSONL (paginates under the hood)
lw list --user turntrout --limit 20
lw list --view top --after 2026-01-01 --limit 100
lw list --view new --body          # include bodies (bulk download)

# full comment thread, depth-first order with depth markers
lw comments iKm2FhpWkuuBojm82

# same API on the EA Forum
lw --site https://forum.effectivealtruism.org get <ref>
```

`get`/`comments` accept a post URL, `_id`, or slug. `--json` on either
returns the raw API payload instead of markdown.

## Library

```python
import lesswrong as lw

post = lw.get_post("why-i-left-google-deepmind")     # dict incl. contents.markdown
posts = lw.list_posts(user="turntrout", limit=20)    # metadata dicts
comments = lw.get_comments(post["_id"])              # thread order, depth annotated
md = lw.render_post(post, comments)                  # frontmatter + body + thread
```

`lw.gql(query, variables)` is the escape hatch for arbitrary GraphQL
(e.g. the `scoreExceeded*Date` fields used by the karma-trajectories
experiment).

## Notes

- Anonymous access; be polite (the client retries with backoff on 429/5xx
  and pages at 200 items/request).
- Votes are not public; `baseScore` (karma) and `voteCount` are.
- Draft or logged-in-only content is invisible to this tool by design.
