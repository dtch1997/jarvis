# wiki log

Append-only, newest first. Format: `## [YYYY-MM-DD] <op> | <title>`.

## [2026-07-10] schema | Sibling wiki registered: science-of-midtraining

A second instance of this schema now lives in the science-of-midtraining repo
(sci-mt PR #176): `docs/sources/` (verbatim reports under provenance headers —
a simplification collapsing our separate `raw/` + `sources/` layers into one
file per source) + `docs/wiki/` (distilled pages only). Added
`entities/scimt-wiki.md` as the discovery pointer; wiki tooling
(ingest/query/lint skills, the consolidation cron) should target "wikis with
this schema", not this directory alone. Touched: entities/scimt-wiki (new),
index.

## [2026-07-09] consolidate | Memory-consolidation pilot: sleeper-cluster memories

First run of the memory-consolidation loop (`.claude/skills/memory-consolidate`).
Persisted memory-only nuggets into the wiki: the depth arms are
parameter-budget-matched (64.2M) so depth ≠ footprint (detail lost when the
4-arm report was deleted from the rsa repo), and the refuge's
attack-strength-dependence framing (mid rung: all-layers most retentive).
Touched: layer-depth-effects, robust-sleeper-agents entity. The four sleeper
memories were compressed to pointer stubs (operational facts retained).

## [2026-07-09] ingest | Sleeper-cluster pilot: four robust-sleeper-agents reports

Bootstrapped the wiki with the sleeper-agent durability cluster. Copied 4 raw
sources (depth study, dynamics post-mortem, scaling sweep from lab-notes PR
#27, pirate pilot from rsa branch `scaling-sweep`) and wrote: 4 source pages, 5
concept pages (backdoor-durability, layer-depth-effects, scale-effects,
attack-specificity, subspace-interference), 2 entity pages
(robust-sleeper-agents, qwen3), 1 synthesis
(what-makes-a-backdoor-durable), index. Cross-source tensions recorded: the
depth study's headline is doubly qualified (scale-emergent, attack-specific);
the mid-late sweet spot from the single-seed pilot is dead.

## [2026-07-09] schema | Initial schema

wiki/CLAUDE.md v1: Karpathy LLM-wiki pattern (raw/sources/concepts/entities/
syntheses + index + log), OKF frontmatter, epistemic-status convention
(firm/partial/pilot/open), ingest/query/lint workflows.
