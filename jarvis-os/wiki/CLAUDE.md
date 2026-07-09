# wiki/ — the jarvis research wiki (schema)

This directory is an **LLM-maintained research wiki** in the sense of
[Karpathy's LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
using [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)-style
markdown + frontmatter as the file format. It sits between the researcher and
the raw experiment reports: knowledge is compiled in once (ingest), then
refined, cross-linked, and audited over time — instead of being re-derived from
the raw reports on every question.

## Layers

- `raw/` — **immutable** verbatim copies of source documents (experiment
  reports, papers). Never edit these; they are the ground truth the wiki cites.
  Each has a provenance entry in `raw/index.md`.
- `sources/`, `concepts/`, `entities/`, `syntheses/` — **wiki pages, owned by
  the LLM.** Create, update, and cross-link freely; every claim must be
  traceable to a page in `raw/` or an external citation.
- This file — the **schema**. Conventions and workflows. Update it when a
  convention changes (and log the change).

## Page types

| type | dir | one page per | purpose |
|---|---|---|---|
| `source` | `sources/` | raw document | faithful summary: question, setup, results, caveats, provenance |
| `concept` | `concepts/` | idea/phenomenon | current best understanding across *all* sources; updated on every relevant ingest |
| `entity` | `entities/` | project, model, dataset, method | reference card: facts, parameters, pointers |
| `synthesis` | `syntheses/` | recurring question | cross-source answer to a question the researcher actually asks; created by query file-back or deliberately |

## Conventions

- Filenames: `kebab-case.md`. Links: relative markdown links
  (from a sibling dir: `[layer-depth-effects](../concepts/layer-depth-effects.md)`) — links are the
  knowledge graph; link liberally.
- Frontmatter (OKF): `type`, `title`, `description` (one line — this is what
  `index.md` shows), `resource` (canonical upstream URL/path), `tags`,
  `timestamp` (last substantive update). Source pages add `source_date` and
  `status` (`firm` / `partial` / `pilot`).
- **Epistemic status is load-bearing.** Mark claims `[firm]`, `[partial]`,
  `[pilot]`, or `[open]` where strength matters. A wiki that flattens a 3-seed
  pilot and a 60-cell sweep into the same voice is worse than no wiki.
- Numbers travel with their error bars and conditions (model, seeds, attack
  rung). Never quote a headline number stripped of its regime.
- Contradictions and qualifications between sources are **content**: state them
  in the relevant concept page under a `## Tensions` heading, don't silently
  resolve them.

## Workflows

### Ingest (new source document)

1. Copy the document verbatim into `raw/` and add a provenance line to
   `raw/index.md` (where it came from: repo/branch/PR, date).
2. Write its `sources/` summary page.
3. Update every concept page the source bears on; create new concept pages for
   genuinely new ideas (not per-paper — per-*phenomenon*).
4. Update affected entity pages and syntheses.
5. Add the new pages to `index.md`; append an ingest entry to `log.md`.
   A single source should typically touch 5–15 pages; if it touched 1, the
   cross-referencing step was skipped.

### Query

1. Read `index.md` first; open only the pages it points to (grep as fallback).
2. Answer with links to wiki pages; follow through to `raw/` when the question
   needs exact numbers or setup details.
3. **File back:** if the answer required nontrivial synthesis, save it as a
   `syntheses/` page and log it — explorations must compound.

### Lint (periodic health check)

Sweep for, and log findings as a `lint` entry (fix inline or file as issues):
- contradictions between pages, or pages stale relative to a newer source;
- orphan pages (no inbound links) and dangling links;
- claims missing epistemic status or stripped of conditions;
- gaps: questions the corpus raises but no page answers (candidate follow-ups).

## index.md and log.md

- `index.md` — the catalog: every page, grouped by type, one line each (the
  frontmatter `description`). It is the retrieval layer; keep it current.
- `log.md` — append-only, newest first, entries formatted
  `## [YYYY-MM-DD] <op> | <title>` where `<op>` is `ingest` / `query` /
  `lint` / `schema`. Body: what changed and which pages were touched.
