---
name: llm-wiki
description: LLM-maintained research wiki (Karpathy pattern + OKF format) at jarvis wiki/ — sleeper-cluster pilot ingested; jarvis PR
metadata: 
  node_type: memory
  type: project
  originSessionId: 9004d12a-06bd-4fe1-9d79-aed4b0e5fe8b
---

Implementation of Karpathy's LLM-wiki gist (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) + Google's OKF markdown/frontmatter format, at `wiki/` in jarvis (**PR #103, MERGED to main 2026-07-09** — wiki/ and .claude/skills/memory-consolidate live on main; the cron's branch-fallback is moot).

Structure: `wiki/CLAUDE.md` = schema (raw/ immutable copies → sources/concepts/entities/syntheses LLM-owned pages; OKF frontmatter type/title/description/resource/tags/timestamp; epistemic-status markers firm/partial/pilot/open; ingest / query-with-file-back / lint workflows), `index.md` = retrieval layer, `log.md` = append-only.

Pilot ingested the [[robust-sleeper-agents]] cluster (4 reports incl. unmerged lab-notes PR #27 + rsa scaling-sweep branch) → flagship synthesis `what-makes-a-backdoor-durable.md`. Pilot verdict: concept pages surface cross-source tensions no single report states (late refuge = scale-emergent AND attack-specific).

**Why:** cross-experiment synthesis was re-derived per question from scattered reports/memory; the wiki compiles it once and compounds.

**How to apply:** when wrapping an experiment with a report, also ingest it into `wiki/` per `wiki/CLAUDE.md`. Next steps parked: /wiki-ingest //wiki-query //wiki-lint skills, hook ingest into "wrap up", periodic lint via [[concierge-tool]] → [[cairn-tool]] issues.

**Second instance (added 2026-07-10):** [[science-of-midtraining]] now hosts a
sibling wiki, same schema (sci-mt PR #176; jarvis PR #107 registered it here
as `wiki/entities/scimt-wiki.md`). Its simplification — `docs/sources/` = ONE
file per source (provenance frontmatter header over the verbatim report body)
instead of separate raw/ + sources/ layers — was Daniel's call and is a
candidate to backport to the jarvis wiki. Wiki tooling (planned
ingest/query/lint skills, the consolidation cron) should target "wikis with
this schema", not `wiki/` alone.

**Memory consolidation (added 2026-07-09):** boundary decided — memory = working set (operational pointers), wiki = canonical findings. `.claude/skills/memory-consolidate/SKILL.md` (same PR #103) encodes PERSIST/COMPRESS/ARCHIVE/KEEP with reversible `memory/archive/`. **Weekly crontab entry, Mon 08:11** (`crontab -l`, headless `claude -p`, log `~/.claude/logs/memory-consolidate.log`). Pilot ran 2026-07-09: 4 sleeper memories compressed to stubs; memory-only nuggets (64.2M budget-matched arms = depth-not-footprint; mid-rung refuge framing) persisted into the wiki.
