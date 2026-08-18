# threads

**Know what you — and your AI agents — actually worked on.**

If you run a lot of Claude Code sessions, activity quickly outruns memory:
projects go quiet without anyone deciding to stop, promising starts get
forgotten, and "what happened this month?" has no reliable answer. Any notes
you keep say whatever was last written, which is not the same thing as what
was done.

`threads` answers from the ground truth instead. It reads your Claude Code
session transcripts, distills each session into a short durable summary, and
groups related sessions into **threads** — one per project — so you can see
where effort is actually going, what's gone dormant, and what fell through
the cracks.

## What it lets you accomplish

- **Fire work off and watch it land.** The **board** (`threads serve`'s front
  page) is a table with one row per thread and three columns — *Prompt* (what
  you asked, typed straight into the top of the table), *Goal* (the drafted,
  inline-editable deliverables + exit criteria the executor is gated on), and
  *Status* (machine-derived lifecycle, live links, and the payoff or the
  question). Rows that need you sort to the top.
- **See your real activity at a glance.** A dashboard of every thread,
  ranked by a tunable relevance score (volume × recency), with 30-day
  sparklines, last-touched dates, sorting, and filters.
- **Catch dropped work before it's lost.** Threads that go quiet get a
  dormancy flag; sessions that match no known project land in an *unfiled
  inbox* instead of vanishing.
- **Park work and pick it back up cheaply.** `threads note` saves a context
  dump (state, next steps, pointers) onto a thread as you step away;
  `threads pickup` prints everything needed to resume — your parked notes
  plus what the transcripts show happened since.
- **See structure you didn't plan.** Clusters of related unfiled sessions
  become auto-drafted *candidate threads*; related threads roll up into
  *programs* and *goals* in a hierarchy view with aggregated stats. Keep
  what's right, delete what isn't — everything auto-drafted is yours to veto.
- **Browse it as a knowledge base.** Everything mirrors into an
  [Obsidian](https://obsidian.md)-compatible vault — plain Markdown,
  frontmatter, `[[wikilinks]]` — so graph view, backlinks, and Dataview
  queries work out of the box.
- **Keep a record that outlives the transcripts.** Claude Code eventually
  ages transcripts out; your summaries persist in `~/.threads/`.

Everything is local files. Summaries never leave your machine, and the tool
never edits your own notes — its outputs are separate, regenerable, and
disposable.

## Quick start

```bash
pip install -e .        # or, in the arsenal workspace: uv sync --all-packages

threads scan            # summarize your recent sessions (see cost note below)
threads weave           # group summaries into threads
threads serve           # open the board (local URL is printed)
```

`scan` uses one small-model call (Claude Haiku) per substantial session —
typically well under a cent each; a 30-day backlog of ~300 sessions costs a
few dollars, and it's capped per run (`--max-calls`, default 100; `--all`
lifts the cap for a backfill). It is incremental and idempotent: re-running
it summarizes only new or grown sessions and costs nothing when there's
nothing new. Trivial sessions (under 10 messages or 5 minutes) are recorded
without a model call. Needs `ANTHROPIC_API_KEY` (or a logged-in `claude`
CLI) for the summarization calls only — `weave`, `serve`, `note`, and
`pickup` make no model calls, except one optional clustering call per
`weave` to draft candidate threads.

## How your work gets organized

- **Session → summary.** Each session becomes one record: a title, a 3–6
  sentence summary of what was attempted and how it ended, artifacts touched
  (branches, PRs, files), and status signals (wrapped-up / blocked /
  abandoned-midstream / ongoing).
- **Summary → thread.** Sessions are matched to threads using deterministic
  signals first — repos touched, git branches, worker-pool metadata — with a
  model-suggested fallback. Unmatched sessions go to the unfiled inbox;
  clusters of them become auto-drafted candidate threads.
- **Your project notes name the threads (optional but recommended).** Point
  `THREADS_MEMORY_DIR` at a folder of Markdown notes, one per project — each
  filename becomes a thread name, and matching keys against note contents.
  An optional `MEMORY.md` index supplies one status line per project;
  threads whose line reads closed/retired/complete are never flagged
  dormant. Without such a folder, threads bootstrap entirely from candidate
  drafts.
- **Threads → programs → goals.** A simple tree in
  `~/.threads/hierarchy.md` (editable Markdown) groups threads under
  mid-level programs; if you keep a goals folder (`THREADS_GOALS_DIR`),
  goal files that mention thread names become top-level roots
  automatically. Every level rolls up its subtree's activity.

## The board (Prompt | Goal | Status)

`threads serve`'s **front page** is the thread board: one row per thread,
three columns, and a text box at the top of the table. It is the working
surface for auto-mode work — fire several threads back to back, then glance
at how each is going. Spec: [`../../docs/thread-board.md`](../../docs/thread-board.md).

```bash
threads serve                 # the board at /, the dashboard at /dashboard
threads board                 # the same rows as text (scripts, shell prompts)
threads board --html          # the served page, to a file or a pipe
threads board --check         # the offline gate (no model calls, no network)
```

**Prompt** — what you said, verbatim. Typing into the box and pressing Enter
*is* `threads launch`: the row appears immediately (optimistic render) while
the durable accept happens in well under 100 ms with no model call, and
routing lands on the row asynchronously. Shift+Enter for a newline; the
copilot toggle and slug autocomplete are the two optional per-row choices.
Observed threads (born from `scan`/`weave`, not the launcher) appear as rows
too, marked `observed`, with their distilled title as the Prompt.

**Goal** — deliverables + exit criteria, agent-drafted and inline-editable.
This is a first-class field on the intent record, not a note: the router
drafts it from the prompt (immediately operative — execution never waits for
you to read it), and the cell expands to show the literal gate. **Editing the
cell is the veto/redirect surface:**

| when you edit | what happens |
|---|---|
| before the executor spawns | the gate is **re-derived from your prose** and the executor is submitted against it — the edit re-specs the task |
| while it runs | the edit is delivered to the worker as a `pool.msg` and the row is **flagged** so the discrepancy is visible; the gate is re-derived only if the executor has not passed it yet |
| after the gate passed | recorded and flagged, but the settled contract is left alone |

**Status** — machine-derived, never self-reported. Launched rows carry the
launcher's termination contract verbatim: `routing → spawning → running →
result | blocked | failed`, derived from the intent record, the concierge task
record on disk, the gate verdict, and the termination sweep's flags. A running
row shows pool status + attempt + cost-so-far + last activity and links to the
deepest live view available (stagehand dashboard → foyer terminal for copilot
rows → log tail). A `result` row renders its deliverable pointers inline (PR,
report, dashboard, branch, gate verdict, the answer file if it exists);
`blocked` renders the actual question; `failed` renders what broke;
contract violations render loud and pin to the top. A worker's own
`result_text` is deliberately never rendered in this column.

Board behaviour:

- **Sort: needs-you first.** Contract violations, then `blocked`, then running
  rows by recency, then everything still starting, then terminal rows.
  Launched rows win ties against observed ones.
- **Archive.** Settled rows older than `board.archive_days` (config.toml,
  default 7) collapse into a labelled, counted archive section, as do parked
  and closed observed threads — nothing is dropped silently, and rows that
  need you are never archived however old.
- **Observed rows** get their own honest state space (`active` / `parked` /
  `blocked` / `closed`) rather than being labelled with an executor lifecycle
  they never had.
- **Responsive** (rows stack into cards on a phone), and **zero model calls
  per page load** — a render is a read of the spool plus a handful of task
  JSONs.
- **Row detail** (the `detail` toggle in each Prompt cell) shows note history,
  the router's interpretation, goal-edit history, and executor handles.
- **Veto affordances** per row: detach, merge-into-thread, and delete for
  auto-drafted candidate threads.

Endpoints behind it (all localhost, all cheap): `POST /launch`, `POST /goal`,
`POST /detach`, `POST /merge`, `POST /candidate-delete`, `GET /tail?tid=…`,
and `GET /dashboard` for the page below.

## The activity dashboard

The observational page stays reachable at `/dashboard` (linked from the board,
and it links back). `threads serve` hosts it locally (or through the
[lobby](../lobby) hub when available), re-rendering every 60 s. You get: the
sortable/filterable thread table (`?sort=relevance|last-activity|sessions|name`,
active-in-N-days / dormant-only / text search — selections stick across
refresh); a collapsible hierarchy tree with roll-ups; a coverage panel
(goals with no active thread, threads under no goal); per-thread drill-down
with artifact links; the unfiled inbox; and candidate threads.
`threads render` prints the same as a Markdown digest; `threads status` is
a one-liner for scripts and shell prompts.

## Launching threads (intent → thread)

Everything above is *observational* — threads are reconstructed after the
fact. The **launcher** is the other direction: declare an intent and a thread
is born to carry it, with an executor spawned to do the work.

```bash
threads launch "summarize this week's eval runs"          # full-auto (default)
threads launch --copilot "pair with me on the parser"     # interactive tmux
threads launch --slug my-project "add the retry path"     # pin the thread
threads launch --dry-run "..."                             # route+stamp, no spawn
```

The **send contract** is deliberately tiny: acceptance persists a durable,
ULID-keyed intent record to `~/.threads/intents/` and returns in well under
100 ms with **no model call and no network**. Routing and spawning are
asynchronous and land *on the thread*, never back at the sender; any failure
becomes a thread note plus a `--sev warn` flare — never silence.

- **Router.** A pinned slug wins; else one cheap model call matches the
  intent against the registry (accepting only an existing slug — attach is
  automatic, no confirmation); else a candidate thread is minted from the
  intent text. The same call drafts the **Goal** (deliverables + exit
  criteria) onto the intent record and writes its interpretation (reading +
  assumptions + chosen gate) as a note, then proceeds — draft-and-veto, never
  blocking. With no model available the Goal still populates from a
  deterministic fallback, and an edit you already made is never overwritten.
- **Modes.** *Full-auto* submits to the [concierge](../concierge) pool with
  the intent + interpretation as the spec seed and the router's gate; the
  concierge tid is recorded on the thread. *Copilot* spawns a tmux `claude`
  seeded with the intent in a fresh `<slug>/<short-ulid>` worktree and records
  the foyer URL.
- **Deterministic weave.** Launcher-born work never relies on heuristic
  matching: the concierge tid and the `<slug>/<short-ulid>` branch namespace
  are stamped at spawn, and `weave` maps those sessions to their slug with a
  pass that runs *before* every heuristic — no model call.
- **Termination contract.** Every launched thread must reach a terminal note
  (`result` | `blocked` | `failed`). A launched intent dormant past
  `launch.terminal_deadline_days` (config.toml, default 3) with no terminal
  note is flagged on the dashboard, raises a `BLOCKED-ON-DANIEL` desk item,
  and flares once.
- **Veto affordances.** Instant creation fragments; *detach* and *merge into
  thread* are one-click actions on each launched intent in the dashboard.

The same code path backs `POST /launch {text, mode?, slug?}` on the threads
server (used by the dashboard's launcher pane) and the CLI.

### Full-auto gate menu

The router picks the concierge gate from a small, documented menu — the gate
is externally checked, never the worker's self-report:

| intent shape | gate | why |
|---|---|---|
| repo-shaped (implement / fix / build / PR / test / refactor…) | `PrOpen()` | done = an open PR |
| compute-shaped (repo-shaped *and* naming a results file, `*.jsonl`/`*.csv`/`*.parquet`) | `PrOpen() & ShellOk("test -s <that file>")` | a PR alone would let a placeholder settle — house rules: results, not artifacts |
| question-shaped (analysis, a number, a written answer) | `ShellOk("test -s .threads-result.md")` | done = a non-empty result file the worker wrote |

The choice is a pure regex over prose (no model, no network — it runs inside
the accept budget) and is stored on the intent record, so it is visible in the
board's Goal cell from the moment the row appears. **The Goal wins over the
prompt**: once the Goal cell holds prose, the gate is derived from *that*,
which is what makes an inline edit able to re-spec the work. A drafted Goal is
derivation-stable — saving it unedited never silently changes the gate.

Override the per-launch budget with `THREADS_LAUNCH_BUDGET_USD` and the
executor's repo with `THREADS_LAUNCH_REPO` (defaults to the git repo at the
launch cwd).

## Parking and resuming work

```bash
# stepping away mid-stream — dump your working context onto the thread:
threads note my-project - --status parked <<'EOF'
## Where this stands
Benchmark runs green; PR not opened yet.
## Next steps
Open the PR; re-run with seed sweep.
EOF

# later, at the top of a fresh session:
threads pickup my-project
```

Notes capture cwd, git branch, and session id automatically, count as
thread activity (a freshly parked thread isn't "dormant"), and can target a
brand-new name to start a thread that has no note file yet. `pickup` prints
the project's status line, all parked notes (newest first), and recent
observed session summaries — a ready-made context pack for you or an agent.

## Open in Obsidian

The vault at `~/.threads/vault/` (refreshed by every `weave`, or on demand
with `threads vault`) mirrors threads, sessions, programs, goals, and
candidates as linked Markdown notes, starting at `INDEX.md`. Open the
folder as a vault (or add it to an existing one): graph view and backlinks
just work, and [Dataview](https://blacksmithgu.github.io/obsidian-dataview/)
can query the frontmatter:

````markdown
```dataview
TABLE relevance, sessions_30d, last_active, dormant
FROM "threads"
SORT relevance DESC
```
````

The vault is a regenerable mirror — safe to delete, never the source of
truth, and pruned of notes whose underlying records vanish.

## Tuning

`~/.threads/config.toml` (written with commented defaults on first run)
holds the knobs: the board's archive window (`[board] archive_days`, 7 days),
the relevance formula's weights
(`relevance = w_sessions·log1p(sessions_in_window) + w_recency·exp(-days_since_last/tau)`;
defaults `1.0` / `2.0` / `tau=7`, 30-day window), the dormancy threshold
(14 days), scan lookback, and clustering minimums. Adjust freely; nothing
else needs to change.

## Automation

`threads` installs no crontab. A daily refresh is one line
(`crontab -e`):

```cron
0 7 * * * cd $HOME && threads scan && threads weave >> $HOME/.threads/cron.log 2>&1
```

Keep the dashboard alive across logout with
`tmux new-session -d -s threads-dashboard "threads serve"`.

For scripting and CI-style gating, `threads scan --check`,
`threads weave --check`, `threads launch --check`, and `threads board --check`
are cheap, offline (zero model calls) health checks that exit non-zero and
print what they verified:

- `scan --check` — summaries complete for the lookback window.
- `weave --check` — match quality above threshold, every concierge session
  resolved, and **100 % deterministic match for launcher-stamped sessions**.
- `launch --check` — one synthetic `--dry-run` launch proves the accept path
  returns <100 ms, then asserts every intent in the spool is consistent (a
  resolved slug + executor handle, a failure note, or still legitimately
  in-flight).
- `board --check` — renders the board from the **live spool read-only** (with
  the model runner stubbed to raise, so a model call on page load is a
  failure), then runs every write-shaped assertion against a fixture spool in
  a temp dir: status derivation for each lifecycle state, Status-column purity
  (a worker's `result_text` must not appear), needs-you sort and archive
  collapse, the Goal edit path (pre-spawn gate re-derivation end-to-end,
  post-spawn `pool.msg` delivery + row flag), and the served surface (board is
  the default page, dashboard is secondary, `POST /launch` durable in <100 ms
  and the row visible on the next render, every veto endpoint wired). It
  prints one PASS/FAIL line per assertion.

## Environment overrides

| variable | points at | default |
|---|---|---|
| `THREADS_HOME` | base dir (`.threads` lives under it) | `~` |
| `THREADS_PROJECTS_DIR` | Claude Code transcript tree | `~/.claude/projects` |
| `THREADS_MEMORY_DIR` | your project-notes folder | `~/jarvis-memory` |
| `THREADS_GOALS_DIR` | your goals folder (optional) | `~/jarvis/goals` |
| `THREADS_CONCIERGE_HOME` | concierge worker pool (optional) | `~/concierge-home` |
| `THREADS_DISABLE_ENQUEUE` | set to `1` to make `launch`'s accept skip the detached router/executor (the seam `board --check` uses) | unset |

Every integration degrades gracefully: with no notes folder, no goals
folder, no worker pool, and no lobby hub, you still get scan → weave →
a local dashboard.

## Privacy

Transcripts can contain sensitive material. Summaries and notes stay under
`~/.threads/` on your machine; nothing is uploaded anywhere except the
transcript excerpts sent to the Claude API for summarization, and the tool
never writes into your notes or transcripts.
