---
name: reports-consolidation-lab-notes
description: Consolidating experiment reports from sdf-hallucination/model-thrashing/science-of-midtraining into lab-notes-jarvis; phase 1 (non-destructive copy) is PR
metadata: 
  node_type: memory
  type: project
  originSessionId: a541c82e-0241-4b1c-9f1d-cca106d7081f
---

Consolidating jarvis experiment write-ups into a single home + gated site in
[[lab-notes-jarvis-spun-out]]. Two-phase by the user's request: **first a
non-destructive copy, verify it's set up nicely, then delete from source.**

**Phase 1 (MERGED — lab-notes-jarvis PR #3, squash `8e2b883` on main):** new
top-level `reports/<project>/` tree. **19 reports, synced from each source
repo's `origin/main`** (the local clones were stale — mt was 23 behind, sci-mt
6): sdf-hallucination (6; canonical home of `collateral-hallucination` +
`reference-class-spread`, which mt has since deleted), model-thrashing (7:
belief-thrashing eval/at-scale, logit-ban ±reasoning, seahorse,
olmo-thrashing-interim, value-thrashing), science-of-midtraining (blogpost + 5
incl. `findings/msm-vs-sft`; its 6 literature notes folded into
`notes/literature/`). ALWAYS re-read source `origin/main` (clones drift).
Wiring: `gather_reports()` in `site/build.py` + `site/report_template.html`;
`md_to_html` gained fenced code / h3–h6 / `---` / ordered lists / report-only
relative-links (notes output unchanged); reports always ship (not
`publish:`-gated); figs inline via the access-code gate; `pages.yml` watches
`reports/**`.

**Landing redesign (done, same branch):** `template.html` now a minimal
"jarvis lab notes" header with a 4-tab toggle — Experiment reports (single
column grouped by project) / Atomic notes (=evergreen) / Literature notes /
Other (posts + working notes); sliding-pane mechanic preserved on note click.
Preview served via [[marquee-tool]] (`serve()`, cloudflare) over the GATED
build (code `jarvis`) — NOT ferry (that's file push/pull).

**Phase 2 (DONE — retire source copies):** sdf-hallucination PR #4,
model-thrashing PR #21, science-of-midtraining PR #131 (all MERGED). Each: git rm
the consolidated write-ups + its `pages.yml` (retired 3 live Pages sites) + a
pointer README → lab-notes. sdf `flywheel.toml` lost its "recent reports" context
source. sci-mt gutted of prose (blogpost/lit-notes/report.md/render_draft.py) but
KEEPS experiment specs/code/data + `findings/msm-vs-sft/*.json{,l}` (lab-notes
links to them). Also fixed a consolidation bug first (lab-notes PR #5): olmo
report figs were under `olmo_figs/` not `figs/` and hadn't been copied.
Consolidation fully complete; lab-notes is now the single source.

Open question flagged in PR #3: sci-mt blogpost overlaps the existing lab-notes
post `site/posts/midtraining-inductive-bias/` — decide later whether to retire one.
