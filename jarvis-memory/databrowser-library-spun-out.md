---
name: databrowser-library-spun-out
description: "databrowser — pip-installable JSONL data-browser library (schema-validate → static HTML browser → Cloudflare serve, declared categorical/continuous filters); dtch1997/databrowser (public), gitignored clone at repos/databrowser"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4794a237-2030-4c00-acb2-2422837280cc
---

Minimal **library** (not the subagent) for browsing JSONL data, built fresh
2026-06-25 and spun out to **dtch1997/databrowser** (PUBLIC, like
[[cowrite-tool]]); gitignored clone at `repos/databrowser`. Distinct from the
[[data-browser-subagent]] (jarvis PR #85) — that's a driver/subagent; this is a
pip-installable package the user asked for explicitly.

API surface (~880 lines, stdlib-only, package `databrowser`):
- `serve(data, *, filter_fields=None, title=None, strict=True, out_dir=None, port=None, tunnel=True) -> Viewer` — build + run http.server + `cloudflared` quick tunnel detached; `Viewer.url`/`.alive`/`.stop()`.
- `build(data, out_dir, *, filter_fields=None, ...) -> Path` — write static `index.html`+`data.jsonl`+`meta.json` only.
- `validate_schema(records, *, strict=True)` — strict (default) requires every record share record 0's keys, else SchemaError; `strict=False` → union.
- `FilterField(name, kind=None)`, `load_records`, CLI (`databrowser serve|build`).

Design decisions the user fixed: **`filter_fields` is an optional kwarg, default
None ⇒ nothing filterable**. Each field's kind is inferred (numeric non-bool ⇒
continuous interval filter; else categorical subset-of-values filter) or forced
via FilterField. `data` = path to .jsonl/.json OR in-memory list[dict].
Front-end = sidebar entry list + full-entry pane, categorical checkboxes (OR
within field, AND across) + continuous min/max inputs + free-text search.
16 pytest tests pass; front-end filter logic verified under node; serve()
smoke-tested (port-readiness probe + zombie-aware `alive`). Same Cloudflare
service pattern as [[data-browser-subagent]] / report-viewer.
