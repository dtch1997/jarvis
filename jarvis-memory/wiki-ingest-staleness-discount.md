---
name: wiki-ingest-staleness-discount
description: Wiki promotion must be earned by expected future reference — staleness/relevance gate on ingestion; one-offs from closed threads stay as stubs
metadata:
  type: feedback
---

Daniel, 2026-08-16, reacting to the ~15-item ingest queue from the first
full-corpus consolidation: "A lot of it isn't relevant anymore, e.g.
thrashing, llm attractors… time / staleness should be accounted for when
deciding what to ingest into a wiki. Things that were one-off / pretty old
might not need to be maintained."

**Why:** every wiki page has a standing maintenance cost (curation, index,
tension-tracking). A true-but-never-again-consulted finding is better left as
a memory stub + git history at zero maintenance cost. Ingest queues are
expiring candidates, not debt.

**How to apply:** encoded as the "Relevance gate" in
`.claude/skills/memory-consolidate/SKILL.md` (jarvis PR #125) — persist only
if tied to an active goal/program/testbed, a recurring method, or already
referenced/contradicted by other pages; re-judge inherited queues each run.
The same taste generalizes beyond the wiki: prefer letting cold artifacts
rest in git over migrating them forward (cf. the [[llm-wiki]] loop and the
2026-08-15 folder pruning).
