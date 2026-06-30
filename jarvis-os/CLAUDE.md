# jarvis

## Keywords

Shorthand directives I use. When I type one, treat it as the instruction below.

- **"SG"** / **"sounds good"** — approval to proceed with everything the agent
  just suggested. Go ahead and do it all without asking again.
- **"SOP"** / **"follow SOP"** / **"SOP applies"** — run my default research
  workflow (see the [SOP](#sop--standard-operating-procedure) section below).
- **"wrap up"** — close out the current piece of work (usually an experiment):
  1. Commit all changes on the worktree branch and open a PR.
  2. Make sure any novel findings are **reproducible** — the spec/command that
     produced them is committed, seeds/config are captured, and a fresh run
     would regenerate the result.
  3. Make sure any artifacts (model checkpoints, eval results, datasets, etc.)
     are **persisted appropriately** — large artifacts to
     `gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/`,
     with a pointer (path/URL) committed in the repo rather than the bytes.

## SOP — standard operating procedure

When I say **"SOP"**, **"follow SOP"**, or **"SOP applies"**, treat it as a
single directive that bundles my default research workflow. Run the steps below,
**applying each only when it's relevant to the task** — always do setup (1–2);
do 3–5 only when the task actually involves experiments / results / a report.
Don't manufacture an empty databrowser or report for a task that has no data.

1. **Worktree.** Sync `main` and create a fresh worktree on a dedicated branch
   for the work — `git fetch && git worktree add .claude/worktrees/<branch> -b
   <branch> main` (cf. the pinned-main + worktree convention). Do every edit
   from inside that worktree.
2. **Task list.** Lay out the work as a task list (TodoWrite) before starting,
   and keep it updated as steps complete.
3. **Run experiments → `stagehand`.** Orchestrate and monitor work with the
   `stagehand` declarative DAG engine (`repos/stagehand`): declare steps with
   `Flow.map`/`filter`/`reduce`/`expand` (or the `do`/`fanout`/`retry` DSL),
   `await flow.run()`, and serve the live graph (`live_dashboard` + `serve`).
   Don't hand-roll progress tracking or the staircase (`stage`/`gate` are gone).
4. **Show results → `databrowser`.** Surface results to me with `databrowser`
   (`repos/databrowser`) — `databrowser.serve("results.jsonl",
   filter_fields=[...])` → give me the `*.trycloudflare.com` URL.
5. **Show reports → `cowrite`.** Serve any report/write-up with `cowrite`
   (`repos/cowrite`: `cowrite serve report.md`) so I can edit in the browser and
   you re-read on ⌘S — not a static dump.
6. **RunPod compute → `bellhop`.** For any job that needs an ephemeral RunPod
   pod (remote GPU/CPU), drive it with `bellhop` (`repos/bellhop`) — the async
   REST lib that checks code into a pod, runs it, brings results back, and checks
   out (pluggable readiness probe + native TTL). Don't hand-roll `runpodctl` /
   SSH provisioning.

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
