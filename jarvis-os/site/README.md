# site/

Live: https://arcadiaimpact.github.io/jarvis/ (public allowlist subset)

Static dashboard generator for `notes/` — Matuschak-style sliding panes, wiki-links open chained panes rightward, backlinks computed at build time. Stdlib Python only.

- Build: `python3 site/build.py` → `docs/index.html` (single self-contained file)
- View locally: `open docs/index.html`
- Deploy: `.github/workflows/pages.yml` builds with `--public` — only notes with frontmatter `publish: true` ship (the site is world-readable; Team plan has no Pages access control). The workflow self-enables Pages on first run.

`docs/index.html` is committed so the dashboard is viewable without running anything.
