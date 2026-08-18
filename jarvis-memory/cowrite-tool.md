---
name: cowrite-tool
description: "cowrite — pip-installable browser-based Markdown co-writing tool (edit in browser, Cmd+S saves back to disk so the AI re-reads & keeps writing); lives at dtch1997/cowrite (public)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: dcedc1ed-6a78-412e-bdee-ad03efa8f71c
  modified: 2026-08-17T23:51:55.416Z
---

`cowrite` is a pip-installable library for co-writing Markdown drafts with the AI in the browser. It's the writable sibling of the `report-viewer` subagent: `cowrite serve draft.md` opens a side-by-side editor (raw Markdown | rendered HTML preview) over a Cloudflare quick tunnel; **Cmd/Ctrl+S writes the edited Markdown back to the file on disk and re-renders**, so the loop is: AI drafts → human edits in browser & saves → AI re-reads the same file & keeps writing, many rounds, no copy-paste.

**Why:** Daniel wanted a frictionless multi-round blogpost co-writing tool for JARVIS-on-a-remote-box; the draft lives on the box, he edits from his laptop.

**How to apply:** `cowrite serve <draft.md> [--slug NAME] [--title T] [--no-tunnel]`, plus `list`/`stop`/`prune`. Figures referenced relatively resolve in the preview (served from the draft's dir; traversal blocked). Detached server+tunnel persist past the CLI; per-slug state under `~/.cowrite/state`. `--no-tunnel` = localhost only (skips cloudflared).

- Migrated 2026-06-22 from ArcadiaImpact/cowrite (private) to **dtch1997/cowrite** (PUBLIC, personal GitHub); `origin` repointed there. In jarvis it's a gitignored clone at `repos/cowrite` (repos/ is gitignored), NOT in-tree.
- Public install works: `pip install git+https://github.com/dtch1997/cowrite` (verified in a fresh venv). On this box it's an editable install pointing at `repos/cowrite` on `main`, so local edits to `main` take effect immediately (no reinstall).
- Draggable center divider landed on `main` (commit 6c3ec6c). An image-upload feature (drag/paste/file-picker → POST /upload) was attempted and ABANDONED — never worked through the remote tunnel browser; worktree deleted.
- src-layout package (`src/cowrite/`: render/server/manager/cli); deps markdown+pygments; needs `cloudflared` on PATH for tunnel mode. Mirrors report-viewer's detached-service + state/teardown model.
- Candidate follow-up: wrap as a `cowrite`/`draft-editor` subagent (sibling to report-viewer / [[data-browser-subagent]]) so "serve the draft" just works.
- **v0.2.0 (PR #2, 2026-07-02): fixed a total editor breakage** — the revert-button commit (PR #1) put `'\n'` inside inline-JS strings of the non-raw Python page template → real newline inside a JS string literal → SyntaxError → whole editor script dead (Save/⌘S/Revert all no-ops, "saving doesn't work"). Regression tests now `node --check` the emitted `<script>`. Same PR made the editor disk-aware: every response carries a content-hash `rev`; `/save` sends `X-Base-Rev` and 409s on conflict (prompt decides which version wins); page polls `/api/state` every 2s and self-refreshes from `/api/doc` when the file changes under a clean editor. GOTCHA: long-lived detached editors keep serving old code until `cowrite stop <slug>` + re-serve.

**2026-07-10:** moved into [[arsenal-monorepo]] as `packages/cowrite` (history preserved); `repos/cowrite` is now a symlink into `repos/arsenal`; dtch1997/cowrite ARCHIVED with a pointer note.

**2026-08-17:** UX roadmap specced with Daniel — arsenal issue #52 ("Google-Docs-style collaboration UX"). Priority: (1) anchored comments stored as inline HTML comments `<!-- cowrite[daniel]: … -->` in the draft itself (AI sees them on re-read; resolve = delete marker), (2) debounced live preview + co-writer presence chip, (3) git-backed version-history panel, (4) visual polish. **Deliberate non-goal: WYSIWYG** — md round-trip normalization would rewrite whole files on every save and poison the AI/git diff loop. Stack stays stdlib + vanilla JS, all writes through the existing rev-conflict path.

**2026-08-17 (later): #52 SHIPPED — all four features merged, issue closed.** Concierge workers built all four; merged sequentially with manual conflict rebases (union-style, render.py template hot spot): #57 comments (t-0817-a7fb) → #55 live preview + presence (t-0817-a1f7) → #56 history panel (t-0817-1090) → #59 polish/⌘BIK shortcuts (t-0817-532f, CodeMirror deliberately skipped). Combined 33-test suite green at f22cc32. Gotchas: comments insert/resolve need a clean editor (server offsets); Revert button still uses old /revert (deliberate); **long-lived detached editors serve old code — `cowrite stop <slug>` + re-serve to get the new UX**. Parallel-then-join dispatch gap → arsenal issue #54.
