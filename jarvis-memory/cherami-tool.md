---
name: cherami-tool
description: "minimal French-learning system — write letters, Claude distils gaps into SRS cards; Claude-is-tutor + JSONL-is-database; dtch1997/cherami (public), clone at repos/cherami"
metadata: 
  node_type: memory
  type: project
  originSessionId: a36551bd-38a7-4036-aa54-612db42b219c
---

cherami = minimal system to learn French, structured around things the user
wants to say. Loop: user writes a letter in French (`letters/NNN-topic.md`,
English/`[gap]` where stuck) → Claude corrects + lists gaps → distils each gap
into a card via `python3 cherami.py add` (capturing the *general principle* in
`note`, not just the fix) → review with `cherami.py due`/`grade ID again|good|easy`.

Design (chosen 2026-06-29): **Claude is the tutor, a file is the database** — no
app server, no LLM API plumbing. Form factor "Claude + a data file"; tutoring
done by me in-session; SRS = provisional SM-2-lite isolated in `schedule()`
(swap for FSRS/Anki-export later). Card store is `cards.jsonl`. CLI is
stdlib-only; this box has `python3` not `python`.

dtch1997/cherami (public), gitignored clone at repos/cherami. See its README
"For Claude" section for how to drive correction + review. Same spinout pattern
as [[cowrite-tool]], [[databrowser-library-spun-out]].

**2026-07-10:** PARKED — dtch1997/cherami ARCHIVED (not under active development; card data stays in the repo, unarchive to resume). Clone repos/cherami remains.
