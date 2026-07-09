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
   `Flow.map`/`filter`/`reduce`/`expand`/`spawn` (+ `best_of`/`with_retry`
   policies), `await flow.run()`, and serve the live graph (`live_dashboard` +
   `serve`). Don't hand-roll progress tracking or the staircase (`stage`/`gate`
   are gone, and so is the `do`/`fanout`/`retry` DSL — removed in v2.0.0).
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
   SSH provisioning. **Pre-flight the pin set locally before launching** —
   `uv pip compile` the exact requirements the pod will install; dependency
   conflicts discovered on-pod burn pod-hours (a `numpy`/`vllm` conflict once
   cost two full pod rounds).
7. **Dispatch autonomous work → `concierge`.** Well-specified work whose output
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
