# site/

Static dashboard generator for `notes/` — Matuschak-style sliding panes, wiki-links open chained panes rightward, backlinks computed at build time. Stdlib Python only.

- Build: `python3 site/build.py` → `docs/index.html` (single self-contained file)
- View locally: `open docs/index.html`
- Deploy: `.github/workflows/pages.yml` is ready but **Pages is intentionally not enabled** — repo is private with unpublished findings, and a Pages site would be public. To go live: Settings → Pages → Source: "GitHub Actions", then push or run the workflow.

`docs/index.html` is committed so the dashboard is viewable without running anything.
