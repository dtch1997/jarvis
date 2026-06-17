# site/

Live: https://arcadiaimpact.github.io/jarvis/ (public allowlist subset)

Static dashboard generator for `notes/` — Matuschak-style sliding panes, wiki-links open chained panes rightward, backlinks computed at build time. Stdlib Python only.

- Build: `python3 site/build.py` → `docs/index.html` (single self-contained file)
- View locally: `open docs/index.html`
- Deploy: `.github/workflows/pages.yml` builds with `--public` — only notes with frontmatter `publish: true` ship. The workflow self-enables Pages on first run.

`docs/index.html` is committed so the dashboard is viewable without running anything.

## Access-code gate

GitHub Pages serves the site publicly (Team plan; native access control needs
Enterprise), so the deploy adds a soft login: every shipped page is encrypted
behind a single shared **access code** and a small in-browser decrypt shell
(`site/gate.py` + `site/gate.html`). A visitor enters the code once (remembered
in `localStorage`); the page is decrypted client-side. Plaintext never ships.

- **Set the code** as a repo Actions secret named `SITE_ACCESS_CODE`
  (Settings → Secrets and variables → Actions). Share it with your teammates.
- The `--public` build **refuses to run** without `SITE_ACCESS_CODE`, so the
  site can never deploy world-readable. To rotate the code, just change the
  secret and re-run the deploy.
- Local builds (`python3 site/build.py`, no `--public`, no code) stay plaintext
  for easy preview. To preview the gate locally:
  `SITE_ACCESS_CODE=test python3 site/build.py --public && open docs/index.html`.

Crypto (stdlib only, mirrored by the shell's `SubtleCrypto` JS): PBKDF2-HMAC-
SHA256 derives an encrypt+MAC key from the code; HMAC-SHA256 counter mode is the
keystream; encrypt-then-MAC authenticates. This is "shared static secret" grade
— enough to keep a small site private, not for high-value secrets. Anyone with
the code can read or reshare the content; there is no per-user revocation.
