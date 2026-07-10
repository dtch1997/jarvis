---
type: entity
title: science-of-midtraining wiki (sibling wiki)
description: Sibling research wiki, same schema as this one, living in the science-of-midtraining repo (docs/wiki + docs/sources) — holds the midtraining program's knowledge; query/lint/consolidate tooling should cover it too.
resource: repos/science-of-midtraining/docs/wiki/index.md
tags: [wiki, midtraining, sibling-wiki]
timestamp: 2026-07-10
---

# science-of-midtraining wiki

A second instance of this wiki schema, repo-local to
`repos/science-of-midtraining` (ArcadiaImpact/science-of-midtraining,
private). Established 2026-07-10 (sci-mt PR #176).

- **Layout:** `docs/sources/` = source archive (one file per report:
  frontmatter header with provenance/`source_date`/`status` over the
  **verbatim** report body — a deliberate simplification of this wiki's
  separate `raw/` + `sources/` layers); `docs/wiki/` = distilled knowledge
  only (`concepts/`, `entities/`, `syntheses/`, `index.md`, `log.md`, schema
  in `docs/wiki/CLAUDE.md`). Same epistemic markers
  (`firm`/`partial`/`pilot`/`open`), same ingest/query/lint workflows.
- **Division of labor in that repo:** `experiments/` is an ephemeral lab
  notebook (merged freely, prunable); durable insight enters the wiki via
  ingest at experiment wrap-up.
- **Why it's separate:** the midtraining program's findings belong with that
  repo; this wiki holds the sleeper cluster and cross-project knowledge.
- **Tooling note:** any wiki tooling built here (ingest/query/lint skills,
  the weekly consolidation cron) should treat "wikis with this schema" as the
  target, not this directory specifically — this page is the discovery
  pointer for the second instance.

Entry point: `repos/science-of-midtraining/docs/wiki/index.md`. First
ingested cluster: stage-placement / midtraining-as-precursor (order-swap,
stage comparison, MSM×EM interaction).
