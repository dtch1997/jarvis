# jarvis

JARVIS is a **command center for high-throughput AI work**: many autonomous
work-threads (sessions, concierge workers, arch2 fleets, pod jobs) run
concurrently; this repo holds the durable state they flow through, and
Daniel's attention is the scarce resource the architecture optimizes.
Jarvis is the **meta-level system, not the object-level work**: projects
live in dedicated repos cloned under `repos/` (spin-out is the expected
fate of successful work; jarvis commits pointers, never their code — see
README "the repos/ pattern"). The design doc — layer model, desiderata,
pain points, build order — is
[`docs/command-center.md`](docs/command-center.md).

## Keywords

Shorthand directives I use. When I type one, treat it as the instruction below.

- **"SG"** / **"sounds good"** — approval to proceed with everything the agent
  just suggested. Go ahead and do it all without asking again.
- **"SOP"** / **"follow SOP"** / **"SOP applies"** — run my default research
  workflow (see the [SOP](#sop--standard-operating-procedure) section below).
  NB the SOP applies **by default** even without this keyword; typing it just
  invokes it explicitly.
- **"wrap up"** — close out the current piece of work (usually an experiment):
  1. Commit all changes on the worktree branch and open a PR.
  2. Make sure any novel findings are **reproducible** — the spec/command that
     produced them is committed, seeds/config are captured, and a fresh run
     would regenerate the result.
  3. Make sure any artifacts (model checkpoints, eval results, datasets, etc.)
     are **persisted appropriately** — large artifacts to
     `gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/`,
     with a pointer (path/URL) committed in the repo rather than the bytes.
- **"park"** / **"park this"** — the lighter cousin of "wrap up", for
  switching away mid-stream: dump the working context durably with
  `threads note <slug> - --status parked` (see the parking convention under
  [Attention routing](#attention-routing--flare--desk--threads)) — state,
  next steps, open questions, pointers to branch/PR/artifacts — then move
  on. No PR required; uncommitted work should at least be pushed on its
  branch and pointed to from the note.

## Goals — the direction layer

`goals/` holds the standing high-level goals (one file per goal; format and
ownership rules in `goals/README.md`). Research sessions should read the
relevant goal file at the start (frontier + interestingness rubric live
there) and, at wrap-up, append dated bullets to its Frontier / Active
threads / Parked follow-ups sections. Ownership is **draft-and-veto** (see
`goals/README.md`): agents draft everything, including Vision/rubric and
candidate new goals (marked `agent-drafted, standing until Daniel edits`),
and drafts are immediately operative — direction never blocks on me. I edit
or veto lazily; the only things that wait for my explicit call are flipping
`automation` to `dispatch` and setting real budgets. `/goal-review` runs a
propose-only portfolio review across active goals.

## Attention routing — flare + desk + threads

Three arsenal tools carry the "how does the system ask for Daniel?" and
"how does context survive a context-switch?" layer:

- **`flare "msg" --sev info|warn|page`** — the universal push channel to
  Daniel (Slack `#jarvis-flares` once the webhook is configured; always
  spooled to `~/.flare/log.jsonl`). **Sanctioned for any agent, any time,
  any reason — the bar is LOW.** Blocked on a credential, a decision, a
  budget, an anomaly, or genuinely unsure? Send a flare; a wasted flare
  costs seconds, a silent stall costs days. Works from sessions, concierge
  workers, pod scripts, and crons (stdlib-only).
- **`desk`** — the waiting-on-Daniel inbox: aggregates blocked/failed pool
  tasks, open-PR ages, `BLOCKED-ON-DANIEL` markers, and recent flares into
  one page (`desk render|digest|sync|serve`; hourly `desk sync` cron pushes
  newly-appearing items as flares).
- **Marker convention**: anything in a memory stub, goal file, or doc that
  waits on Daniel gets a line containing **`BLOCKED-ON-DANIEL:`** followed
  by what's needed — that string is what desk sweeps for. Add it when you
  park work on him; remove it when unblocked.
- **`threads note` — parking convention**: when a session (or worker) steps
  away from live work mid-stream, dump the context onto its thread before
  switching: `threads note <slug> - --status parked` with a markdown body
  (state, next steps, open questions, branch/PR/artifact pointers) on
  stdin; slug = the memory-stub name, or a new kebab-case name if no stub
  exists yet (the note seeds a candidate thread). **Sanctioned for any
  agent, low bar** — the observed scan layer only sees
  "abandoned-midstream"; the note is what makes pickup cheap. Resume with
  `threads pickup <slug>` at the top of the next session. Notes are spool
  files (`~/.threads/notes/`), not memory stubs — durable distillation into
  `~/jarvis-memory`/wiki stays with memory-consolidate.

## SOP — standard operating procedure

**The SOP applies by default — to every research/experiment task, unless I
explicitly say otherwise.** Don't wait for the keyword; saying **"SOP"** /
**"follow SOP"** / **"SOP applies"** just invokes it explicitly. Run the steps
below, **applying each only when it's relevant to the task** — always do setup
(1–2); do 3–6 only when the task actually involves experiments / results / a
report. Don't manufacture an empty databrowser or report for a task that has
no data. The tool bindings below are defaults, not suggestions — in
particular, any multi-step experiment pipeline (sweep, gen→train→eval chain,
fan-out) goes through `stagehand` (step 3); don't hand-roll orchestration,
retry loops, or progress tracking that a bound tool owns. This applies to
concierge workers too (mirrored in `~/concierge-home/HOUSE_RULES.md`) — task
specs should assume it rather than restate it.

**Tooling home — the `arsenal` monorepo.** All bound utilities (stagehand,
bellhop, databrowser, cowrite, concierge, plus lobby/ferry/cairn/reportly)
live in one uv workspace at `repos/arsenal` (`packages/<tool>`, one root
`.venv` via `uv sync --all-packages`); the old `repos/<tool>` paths are
symlinks into it. New utilities are born as arsenal packages, not new repos.
Serving tools (databrowser/cowrite/stagehand dashboards) register with the
shared `lobby` hub — one tunnel + one index page (`lobby status` prints the
URL); the links I get are `https://<hub>…/a/<name>/`, not one tunnel per app.

1. **Worktree.** Sync `main` and create a fresh worktree on a dedicated branch
   for the work — `git fetch && git worktree add .claude/worktrees/<branch> -b
   <branch> main` (cf. the pinned-main + worktree convention). Do every edit
   from inside that worktree.
2. **Task list.** Lay out the work as a task list (TodoWrite) before starting,
   and keep it updated as steps complete.
3. **Run experiments → `stagehand`.** Orchestrate and monitor work with the
   `stagehand` declarative DAG engine (`repos/stagehand`): declare steps with
   `Flow.map`/`filter`/`reduce`/`expand`/`spawn` (+ `best_of`/`with_retry`
   policies), `await flow.run()`, and serve the live graph (`live_dashboard` +
   `serve`). Don't hand-roll progress tracking or the staircase (`stage`/`gate`
   are gone, and so is the `do`/`fanout`/`retry` DSL — removed in v2.0.0).
   **Monitors watch loops, not steps**: every training/eval loop ticks a
   monitor — `t = track(batches, "train")` … `t.set(loss=…)` (tqdm-shaped),
   or `m.update(loss=…)` per step — including inside subprocess training
   scripts, where the parent step passes `env={**os.environ, **monitor_env()}`
   so the child's ticker nests under the task on the dashboard. Never wrap a
   whole step in `monitor(total=1)` with `set(status=…)` + one final
   `update()` — the engine already tracks step state; that pattern shows no
   progress and now logs a warning.
4. **Show results → `databrowser`.** Surface results to me with `databrowser`
   (`repos/databrowser`) — `databrowser.serve("results.jsonl",
   filter_fields=[...])` → give me the hub URL it returns
   (`https://<hub>…/a/<name>/`).
5. **Plots → `xy`.** Make figures with the `xy` charting library
   (`pip install xy`, reflex-dev/xy) instead of matplotlib. For standard
   pyplot code just swap the import — `import xy.pyplot as plt` — and keep
   the plotting code; use the native API (`xy.line_chart`, `xy.scatter_chart`,
   …) for interactive charts. Export PNG/SVG for reports (`fig.savefig` /
   `chart.to_png`); use `chart.to_html` when the plot is worth panning/zooming
   and serve it like any other page. Verified headless on this box (v0.0.6):
   all exports work; large scatters auto-switch to a density surface (5M
   points → PNG in 0.05s), so don't pre-downsample. It's alpha — if the
   pyplot shim lacks something (twin axes, exotic colorbars), fall back to
   matplotlib for that one figure rather than fighting the shim.
6. **Show reports → `cowrite`.** Serve any report/write-up with `cowrite`
   (`repos/cowrite`: `cowrite serve report.md`) so I can edit in the browser and
   you re-read on ⌘S — not a static dump.
7. **RunPod compute → `bellhop`.** For any job that needs an ephemeral RunPod
   pod (remote GPU/CPU), drive it with `bellhop` (`repos/bellhop`) — the async
   REST lib that checks code into a pod, runs it, brings results back, and checks
   out (pluggable readiness probe + native TTL). Don't hand-roll `runpodctl` /
   SSH provisioning. **Pre-flight the pin set locally before launching** —
   `uv pip compile` the exact requirements the pod will install; dependency
   conflicts discovered on-pod burn pod-hours (a `numpy`/`vllm` conflict once
   cost two full pod rounds).
8. **Dispatch autonomous work → `concierge`.** Well-specified work whose output
   is an artifact with a definition of done (branch wrap-ups, sweeps, report
   pipelines) goes to the worker pool (`repos/concierge`) instead of being held
   in-session. Decision rule: information you need *now* to keep reasoning →
   subagent; a deliverable that should exist even if this session dies →
   concierge. Usage: `CONCIERGE_HOME=~/concierge-home` (daemon lives in tmux
   session `concierge`); `pool.submit(spec, gate=…, output=Dataclass)` or
   `await pool.run(…)` — the gate (`PrOpen()`,
   `ShellOk("reportly lint report.md")`, `&`-composed) defines done, never the
   worker's self-report; `output=` types the returned data. **For compute
   tasks, gate on results, not artifacts**: `PrOpen()` alone lets a worker
   settle "done" with a placeholder report while the experiment still runs on
   an unowned pod — compose in a results assertion, e.g. `PrOpen() &
   ShellOk("test $(wc -l < experiments/<slug>/results.jsonl) -ge <N>")`. Join without
   polling: background a tiny awaiter script (`pool.wait(tid)` then exit) as
   `run_in_background` and act on the `<task-notification>`; answer a `blocked`
   task with `pool.msg(tid, …)`; `pool.ask(tid, …)` rehydrates a settled task's
   session for follow-ups. Worker conventions live in
   `~/concierge-home/HOUSE_RULES.md` (read per-spawn); `config.yaml` is read
   only at daemon startup — restart the tmux session after changing it.

## Merging PRs (pinned-main convention)

Because the primary checkout is pinned to `main` and branches live in
worktrees, `gh pr merge --delete-branch` **always half-fails** here — the
remote merge succeeds but the local branch delete errors with
`'main' is already checked out` or `Cannot delete branch ... checked out at
.claude/worktrees/...`. Don't use it. Instead:

1. `gh pr merge <n> --squash` (no `--delete-branch`),
2. `git worktree remove .claude/worktrees/<branch>`,
3. `git branch -D <branch>` (and `git push origin --delete <branch>` if the
   remote branch should go too).

Always finish a piece of work with its worktree removed — stale worktrees
block branch deletion in later sessions.

## Crontab is a build artifact

The devbox crontab's jarvis entries live between `# BEGIN/END
ArcadiaImpact/jarvis` markers, owned by `ops/install-cron.sh` with
`ops/cron.tab` as the PR-reviewed source of truth. To add/change a cron
job: edit `ops/cron.tab` on a branch, merge, run `ops/install-cron.sh`.
Never `crontab -e` inside a managed block, and never add jarvis-ecosystem
entries outside one. `ops/install-cron.sh --check` diffs live-vs-repo
(exit 1 on drift). Other repos own sibling blocks the same way (e.g.
`repos/investment/ops/cron.tab`); installers never touch each other's
blocks.

## Background tasks (long-running jobs)

The harness fires a `<task-notification>` **only when the process it tracks
actually exits.** Anything that detaches or deadlocks that tracked process
breaks the contract: the job looks like it's "still running" forever and you
end up polling "status?" by hand. A `PreToolUse` hook
(`.claude/hooks/guard-background-tasks.py`, registered in
`.claude/settings.json`) blocks the two anti-patterns below — treat the hook as
a backstop, not a substitute for doing it right.

**The right way — run the real command directly:**

- `Bash(<the actual long command>, run_in_background: true)`. No `nohup`, no
  `&`, no wrapper. Then **wait for the `<task-notification>`; don't poll.**
- One notification *when X is ready* (when you can't run the job in the
  foreground, e.g. waiting on an already-running process's log): background an
  `until` loop that exits on a log marker —
  `until grep -q "Ready in" dev.log; do sleep 0.5; done`.
- One notification *per recurring event* (every ERROR line, every CI step): use
  the `Monitor` tool — each stdout line becomes a notification. Make the filter
  cover failure signatures too (`Traceback|Error|FAILED|Killed|OOM`); silence is
  not success.

**Anti-patterns (the hook blocks these):**

1. **Detaching the real work** inside a `run_in_background` command —
   `nohup`/`disown`/`setsid`, or `cmd & echo launched`. The harness then tracks
   the launcher (which exits instantly), not the job → no completion signal, job
   orphaned.
2. **Self-matching `pgrep -f` watcher** — `while pgrep -f "pattern"; do sleep;
   done` never exits, because `pgrep -f` matches the full command line and the
   loop sees its *own* cmdline. Gate on a log marker or a pidfile instead, and
   verify the loop actually terminates.
