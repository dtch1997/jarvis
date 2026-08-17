# Threads: extraction pipeline + summary dashboard — MVP spec

*2026-08-17 · agent-drafted, standing until Daniel edits · implements the
"Threads — the bottom-up spine" section of
[`command-center.md`](command-center.md)*

## What this is

An arsenal package named **`threads`** (Daniel's pick, 2026-08-17 — the
earlier working name "loom" collides with an existing AI-context term) that
turns raw transcripts into the bottom-up state layer:

```
transcripts ──scan──▶ per-session summaries ──weave──▶ threads ──serve──▶ dashboard
                                                │
                                                └─▶ unfiled inbox + auto-drafted candidate threads
```

- **Summary** = extracted record of one session (what happened, artifacts,
  status signals). Observed, never self-reported.
- **Thread** = a group of related summaries + a distilled note. Thread
  identity keys on the existing memory registry — **one thread = one memory
  slug in `jarvis-memory/`**; there is no second registry (desideratum 2).
  A session + its context is the smallest thread; higher-order threads
  (→ goals) are phase 2.
- **Dashboard** = a lobby-served renderer over summaries + assignments.
  Views, never a source of truth.

Sanctioned by the bottom-up philosophy (2026-08-17): agents generate
threads automatically; Daniel's control is delete/rework, not pre-approval.

## Data sources (verified on this box, 2026-08-17)

| Source | Location | What it gives |
|---|---|---|
| Claude Code transcripts | `~/.claude/projects/<munged-cwd>/<session>.jsonl` | the raw record; ~280 sessions touched in the last 30 days |
| Munged cwd in the dir name | e.g. `...-concierge-home-workspaces-t-0709-3884` | free metadata: concierge tid, repo name, worktree branch are often *in the path* |
| Concierge records | `~/concierge-home/tasks/`, `specs/` | tid → spec → owning project/slug |
| Memory registry | `jarvis-memory/MEMORY.md` + stubs | the thread registry the tool keys against |
| Goal files | `jarvis/goals/` | phase-2 coverage view |

## Commands (MVP surface)

### `threads scan` — summarize new sessions

Incremental sweep of `~/.claude/projects/**/*.jsonl`:

- **Idempotent**: keyed on `(session_id, transcript_size)`; unchanged
  transcripts are skipped, grown ones re-summarized. A no-change re-run
  finishes in seconds and calls no model.
- **Triviality filter**: skip sessions under a threshold (default: <10
  messages or <5 min span) — they get a stub record, no model call.
- **Summarizer**: one headless `claude -p` call per session (haiku-class
  model, JSON-schema output), fed a truncated/downsampled view of the
  transcript (user turns + assistant text + tool names; tool outputs
  elided). Output record:

```json
{
  "session_id": "...", "cwd": "...", "t_start": "...", "t_end": "...",
  "title": "one line",
  "summary": "3–6 sentences: what was attempted, what happened, how it ended",
  "artifacts": {"branches": [], "prs": [], "files": [], "urls": []},
  "status_signals": ["wrapped-up" | "blocked" | "abandoned-midstream" | "ongoing"],
  "candidate_slugs": ["best-guess memory slugs, from the MEMORY.md index shown in-prompt"],
  "keywords": ["for clustering unmatched sessions"]
}
```

- **Cost guardrail**: per-run model-call cap (default 100 sessions/run,
  config knob); flare a warn if the cap truncates a run.

### `threads weave` — match summaries to threads

Deterministic passes first, model assist last:

1. **Concierge**: cwd matches `concierge-home/workspaces/<tid>` → look up
   tid in `~/concierge-home/tasks/` → owning spec/slug.
2. **Branch → slug**: branches touched (from cwd path for worktree
   sessions, plus `artifacts.branches`) matched against memory slugs —
   exact, then normalized-substring. (cwd alone is known-defeated by the
   many-threads-one-repo layout; branch is the primary key.)
3. **Repo → slug**: cwd under `repos/<name>` or a dedicated repo → the slug
   whose stub names that repo.
4. **Model-validated fallback**: the summarizer's `candidate_slugs`,
   accepted only if the slug exists in `MEMORY.md`.

Everything still unmatched lands in the **unfiled inbox**. `threads weave`
then makes one clustering call over unfiled summaries (keywords + titles)
and drafts **candidate threads**: name + one-paragraph distilled note +
member sessions, marked `agent-drafted, standing until Daniel edits`.
Candidate threads live in the tool's store until promoted to a real memory stub
(promotion = memory-consolidate's job, or Daniel's ask); deletion is the
veto.

### `threads serve` / `threads render` — the summary dashboard

`threads serve` registers with lobby → `https://<hub>…/a/threads/`. MVP views:

1. **Thread table** — one row per active memory slug: last-observed
   activity, session count with a 30-day sparkline, latest session title,
   **dormancy flag** (no activity in N days, default 14, while the stub
   says active).
2. **Thread drill-down** — the summaries in that thread, newest first, with
   artifact links (PRs, branches).
3. **Unfiled inbox** — sessions matching no thread, newest first.
4. **Candidate threads** — auto-drafted clusters awaiting promote/delete.

`threads render` emits the same as a markdown digest (future desk/Slack
transport; not wired in MVP).

## Storage

`~/.threads/` spool (same pattern as `~/.flare/`): `summaries/<session>.json`,
`assignments.jsonl`, `candidates/<name>.md`, `state.json` (scan cursor).
Summaries are derived-but-durable — transcripts age out, so the spool is
retained, not treated as a cache. Not git-versioned in MVP; promoting
durable distillations into `jarvis-memory`/wiki stays with
memory-consolidate (phase 2 may sync the spool to a git remote or ferry.cas
if loss ever bites).

## Definition of done (MVP)

Gate-checkable, per house rules:

1. `threads scan` completes over the last 30 days of real transcripts on this
   box; every non-trivial session has a summary record; immediate re-run is
   a no-op in <10 s.
2. `threads weave` auto-matches **≥70%** of non-trivial, non-concierge
   sessions to an existing slug, and **100%** of concierge-workspace
   sessions to their tid's task; the actual match rate is reported, not
   asserted.
3. Dashboard live behind lobby with the four views; the `/a/threads/` URL
   delivered to Daniel.
4. If ≥3 unfiled sessions cluster, at least one agent-drafted candidate
   thread exists to demonstrate the loop.
5. Total model spend for the 30-day backfill reported; subsequent
   incremental runs cost only new sessions.

Suggested concierge gate:
`PrOpen() & ShellOk("threads scan --check && threads weave --check")` where
`--check` exits nonzero unless the corresponding DoD holds.

## Non-goals (MVP)

- Writing into memory stubs (the machine-drafted activity block) — phase 2,
  after match quality is observed.
- Goal-level weaving / recursion above session→thread; threads↔goals
  coverage view.
- Push (desk/flare integration, dormancy alerts), embeddings, real-time
  updates, backfill beyond 30 days (config knob exists).

## Phase 2 sketch (not committed)

Derived activity block in memory stubs → dormancy alerts through desk →
memory-consolidate consumes summaries instead of recall → threads↔goals
coverage feeding `/goal-review` → higher-order thread notes (weave threads
into goal-level narratives). Cron (`ops/cron.tab`) added once the tool
exists: daily `threads scan && threads weave`.
