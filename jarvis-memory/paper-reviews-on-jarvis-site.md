---
name: paper-reviews-on-jarvis-site
description: "Convention for hosting paper reviews as recursive linked-pane reports, and linking the live site in Slack"
metadata: 
  node_type: memory
  type: project
  originSessionId: 94bdcd57-54e7-4475-8b77-a0e74e00f3c8
---

Paper reviews (e.g. AMR-rubric critiques) are hosted as a "recursive report": a
hub exec-summary note that wiki-links into per-section detail notes, reusing the
Matuschak sliding-pane mechanic in `site/build.py` (clicking a `[[link]]` opens
the target in a pane to the right). No special rendering — the drill-down UX is
the pane chain. Figures: markdown `![alt](assets/x.png)`, files under `site/assets/`.

These now live in the spun-out repo [[lab-notes-jarvis-spun-out]] (clone at
`repos/lab-notes-jarvis/`), not in jarvis itself.

**How to add one:**
- Write notes under `notes/literature/` with frontmatter `publish: true` (the
  `--public` CI build ships only published notes; links to unpublished → danglers).
- Structure: hub (TL;DR + supported/not-supported + net) → detail spokes
  (experiment+eval, rung-by-rung verdict) → link to [[amr-stronger-evidence-framework]].
- Don't commit `docs/` from a plaintext local build for deploy — CI rebuilds it
  `--public` + access-code-gated on push to `main`; `git checkout -- docs/` first.
- Commit + push to the lab-notes-jarvis repo → CI deploys to the gated Pages site.

**Standing instruction (user, 2026-06-20):** when posting paper TL;DRs / reviews to
`#lab-notes-jarvis` Slack, link the live write-up on the Pages site
(https://arcadiaimpact.github.io/lab-notes-jarvis/). Style per [[slack-post-style]]
(concise, TL;DR first).
