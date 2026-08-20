# jarvis-artifacts

Registry + sources for **Claude Code artifacts** — the claude.ai-hosted
pages sessions publish (handbooks, demos, decision docs, report views).
Sibling of `jarvis-memory/`, with the opposite orientation: memory is the
private state layer; artifacts are **public-facing rendered views**,
default-private on claude.ai but built to be shared.

## Why this exists

Two failure modes, both observed 2026-08-20:

1. **Orphaned sources.** An artifact's source HTML lived only in a
   session's scratchpad (`/tmp/...`), which dies with the session. The
   next session that wanted to update the page had to reconstruct it by
   fetching the rendered version. The source of a published page is a
   fact worth keeping; scratchpads are not where facts live.
2. **No registry.** 13 artifacts existed with no list of what they are,
   which thread owns them, or whether they're current. "A lot of random
   claude code artifacts" is the observed failure state.

## Conventions

- **Publish from the repo, not the scratchpad.** Any artifact meant to
  outlive its session gets its source committed here first —
  `jarvis-artifacts/<slug>/<name>.html` (or `.md`) — and published from
  that path. Throwaway one-turn artifacts are exempt.
- **Register it.** Every published artifact gets a row in
  [`INDEX.md`](INDEX.md): title, URL, updated date, source path (`—` if
  the source predates this folder and was never committed), owning
  thread slug, status. Draft-and-veto: agents keep the index current;
  uncertain thread attributions are marked `?`.
- **Update flow (any session):** edit the committed source, republish
  passing the artifact's existing `url` — publishing without `url` from
  a new session forks a second artifact, which is the bug this folder
  prevents. Bump the row's date.
- **One source of truth.** The repo file is canonical; the claude.ai
  page is a rendered view. If they drift, the repo file wins — same rule
  the handbook itself states in its colophon.
- **Private-thread artifacts** (e.g. life-theses material) are *listed*
  in INDEX.md for registry completeness but their sources stay in their
  own private repos, not here.

## Relation to lab-notes-jarvis

Unresolved, tracked as a GitHub issue (see INDEX.md header). Both are
public-facing publishing channels: lab-notes-jarvis is the gated
GitHub-Pages site for research reports (submit via
`scripts/submit_report.py`); Claude artifacts are ad-hoc interactive
pages on claude.ai infra. Candidate resolutions: (a) keep both, this
index tracks both; (b) lab-notes becomes a renderer of sources committed
here; (c) artifacts = staging, lab-notes = durable archive. Decision is
Daniel's to veto once a draft proposal exists.
