---
name: lab-notes-jarvis-spun-out
description: The lab-notes site spun out of jarvis into ArcadiaImpact/lab-notes-jarvis with gated GitHub Pages
metadata: 
  node_type: memory
  type: project
  originSessionId: 94bdcd57-54e7-4475-8b77-a0e74e00f3c8
---

The notes dashboard + paper reviews were spun out of jarvis (2026-06-20) into
**ArcadiaImpact/lab-notes-jarvis** (private repo). In jarvis it's now a gitignored
clone at `repos/lab-notes-jarvis/`, NOT in-tree (cf. [[aligne-spun-out-to-own-repo]],
[[open-tinker-infra]]). jarvis PR #82 removed the in-tree `site/`, `notes/`, `docs/`,
`.github/workflows/pages.yml`; the old in-tree review PR #80 was superseded/closed.

- **Live (gated):** https://arcadiaimpact.github.io/lab-notes-jarvis/ — access code `jarvis`.
- Private repo, public Pages (org is Team plan → Pages is world-readable, hence the
  access-code gate via `site/gate.py`). `SITE_ACCESS_CODE` Actions secret = `jarvis`.
- Deploy: `.github/workflows/pages.yml` builds `--public` + gated on push to `main`.
  Pages had to be enabled once (`gh api -X POST repos/.../pages -f build_type=workflow`)
  or the first run hits `startup_failure`.
- **Pages deploys are SLOW here (~9–12 min server-side; 2026-07-02, PRs #13–#16):**
  longer than deploy-pages@v4's hard-capped 10-min poll (values >600000 ms silently
  clamped), so the action's verdict is unreliable — its timeout "cancel" is cosmetic
  (the deployment usually lands minutes after the run "fails") and a still-processing
  deployment 400s the next create ("cancel <sha> first"). The workflow (PR #16) now
  stamps `GITHUB_SHA` → `docs/version.txt` and judges success by polling the live
  site, with one retry create for the occupied-slot 400. NEVER call
  `POST pages/deployments/<sha>/cancel` from the workflow — it succeeds for ANY sha
  and kills the site's ACTIVE deployment (the PR #13 janitor and #14 sweep both
  self-cancelled that way; both reverted). A run marked "failure" does NOT mean the
  site didn't update — check `<site>/version.txt` before re-running anything.
- Authoring: notes under `notes/{evergreen,literature,working}/*.md`, `publish: true`
  to ship; `site/build.py` renders Matuschak panes (now also markdown images via
  `site/assets/` → `docs/assets/`). See [[paper-reviews-on-jarvis-site]].
- **Report submission (2026-07-02, PR #8):** one command from anywhere —
  `python3 scripts/submit_report.py <report.md> --project <proj>` — copies figures
  into `reports/<proj>/figs/`, rewrites refs, lints (missing figure = error),
  smoke-builds, then branch+PR from a temp worktree. `--check` mode = CI lint
  (`validate-reports.yml` on PRs touching `reports/**`). `docs/` is no longer
  committed (gitignored; Pages deploys the CI-built artifact). Don't hand-copy
  reports/figures anymore.
- **Report curation tiers (2026-07-02, PR #11 MERGED):** display-only pruning —
  every report always ships. Frontmatter `featured: true` → ★ highlights strip on
  top of the Reports view (curated shortlist, 8 seeded incl. desire-probe);
  `archived: true` → folded behind an "N archived" toggle in its project group
  (never delete, fold — none archived yet).
  Project filter chips (localStorage) pick which projects render; reports sort
  newest-first, so give new reports a `date:`.
- **Per-post access (2026-07-17, PR #33):** `access: public` in a report's
  frontmatter ships that page ungated (plaintext + figures on disk; gated pages
  inline their copies of shared figures — no leakage). First open post:
  `reports/risk-averse-ai/elliott-note.md`
  (https://arcadiaimpact.github.io/lab-notes-jarvis/reports/risk-averse-ai/elliott-note.html).
- **Unified with cowrite (2026-07-20/22, PRs #36 #37 + arsenal #25):** report
  pages import `assets/notes.css` (distill-flavored; canonical copy in arsenal
  `packages/cowrite/src/cowrite/notes.css`, keep in sync) AND `site/build.py`
  renders through `cowrite.render.render_fragment` (pip dep via arsenal
  subdirectory URL in both workflows) — editor preview ≡ published page.
  Hand-rolled `md_to_html` DELETED. Site-side pre/post: `[[slug]]` links,
  `target=_blank`, **HTML comments stripped at build** (protects
  `<!-- internal: -->` on public pages). `$` convention: plain `$` renders
  fine on both hosts, NO `\$` escaping anymore (old memory note about \$ is
  obsolete). `scripts/check_render.py` asserts all this in validate CI.
- **Experiment archive (2026-06-30):** the dated experiment **runs** were moved out
  of jarvis into this repo at repo-root `experiments/` (21 dirs, ~499 git-tracked
  files; lab-notes PR #1 + jarvis removal PR #95). It's a TRUE MOVE — jarvis no
  longer has the run dirs. jarvis KEEPS only the operating-model/registry docs
  (`experiments/{README.md,EXPERIMENTER.md,prediction-registry.md}`). The archive
  sits OUTSIDE the Pages build (which triggers only on `notes/**`+`site/**`), so it's
  stored but unpublished. New runs still scaffold in jarvis `experiments/<date>-<slug>/`
  and get archived here on wrap-up. Large run **artifacts** (~13 GB across 7 dirs) were
  pushed to `gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/` and
  each archived dir carries an `ARTIFACTS.md` pointer (lab-notes PR #2); the bytes were
  then deleted from the local jarvis checkout. See [[gcs-experiment-storage-convention]].
