# jarvis

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
