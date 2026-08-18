---
name: personal-website-writing-funnel
description: "dtch1997.github.io writing-section upgrade (benchmarked vs naml.us); concierge task t-0818-2f91 → PR \"writing-funnel\"; papers-page upgrade deliberately deferred"
metadata: 
  node_type: memory
  type: project
  originSessionId: 051ec893-3964-46f3-9fbb-6aded536a024
  modified: 2026-08-18T01:20:19.856Z
---

Daniel wants his personal site (dtch1997/dtch1997.github.io, clone
`repos/dtch1997.github.io`) to funnel readers into his posts the way
Geoffrey Irving's naml.us does. Site is zero-dep static: `build.py`
(content.md → index.html) + LessWrong mirror pipeline
(`scripts/fetch_lesswrong.py` → `posts.json`, `build_writing.py` renders
themed post pages, CURATED list = source of truth).

Gap analysis vs naml.us (2026-08-18): post pages already read well; missing
funnel = excerpts (index + homepage), prev/next chaining, RSS, linkable
filters + Latest view, full dates + CC footer. Deliberately NOT copied:
pagination, per-tag pages, his visual design.

Dispatched to concierge 2026-08-18: task **t-0818-2f91**, branch
`writing-funnel`, gate = PrOpen & feed.xml parses & deterministic rebuild
(`git diff --exit-code`). PR is review-only — Daniel merges design changes
himself.

Parked follow-up (ranked below the above by Daniel's agreement): papers
upgrade — thumbnails on the 4 highlighted papers, possibly per-paper detail
pages à la naml.us/paper/<slug> (abstract, figures, links, prev/next).
