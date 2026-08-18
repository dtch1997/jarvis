---
name: background-tasks-no-detach-no-self-match
description: "How to run long jobs so completion actually notifies — never nohup-detach, never pgrep a pattern that matches the watcher itself"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5f1abda5-32fb-4155-90ac-2c5430693051
---

For long-running work (training runs, syncs), run the ACTUAL command as the `run_in_background: true` Bash task. The harness tracks that process and re-invokes me when IT exits. Do not build separate "watcher" scaffolding.

**Two mistakes that made me silently drop tasks (user had to poll "status?" repeatedly, 2026-06-16):**

1. **nohup-detach anti-pattern.** Running `nohup train & echo launched` inside a `run_in_background` command makes the harness notify on the *launcher's* exit (immediate), NOT the training's. The training is orphaned/untracked → no completion signal. Fix: invoke the training command directly with `run_in_background: true`; no `nohup`, no `&`.

2. **Self-matching pgrep watcher (worse).** A wait-loop like `while pgrep -f "battery-sft.*results/msm/s1"; do sleep 30; done` never exits, because `pgrep -f` matches against the FULL command line and the watcher's own cmdline contains the literal pattern string `battery-sft.*results/msm/s1`. The loop sees itself, stays true forever, the tracked command never exits → no notification, and stuck shells pile up for hours. (Confirmed: 5 stuck watcher shells, up to 3h48m old.)

**Why:** completion notifications only fire when the harness-tracked command actually exits. Detaching or deadlocking the tracked command breaks that contract.

**Now enforced (2026-06-16), committed in the jarvis repo (not global):** a `PreToolUse(Bash)` hook `jarvis/.claude/hooks/guard-background-tasks.py`, registered in `jarvis/.claude/settings.json` (command uses `$CLAUDE_PROJECT_DIR` so it's portable across clones/worktrees). Blocks both anti-patterns — `nohup`/`disown`/`setsid` or `cmd & echo` in a `run_in_background` command, and any `while/until` loop polling `pgrep -f`. Exit 2 + stderr; fails open on parse error. Guidance lives in `jarvis/CLAUDE.md` "Background tasks". Scope tradeoff: only active when cwd is inside jarvis (and its worktrees, since the committed file ships with each checkout) — NOT other repos. Verified blocking; the direct script self-test passes.

**How to apply:**
- Default: `Bash(<the real long command>, run_in_background: true)`. Wait for the task-notification; don't poll.
- If a watcher/wait-loop is truly needed, gate on a log completion marker (`grep -q "completed successfully" log`) rather than `pgrep`, OR make the pgrep pattern impossible to self-match (match on a pidfile, or `pgrep -f` a string not present in the watcher's own cmdline). Verify the watcher actually terminates.
- User values not having to investigate dropped tasks — see [[experiments-need-spec-not-permission]] (empowered to run autonomously, so the autonomy must be reliable).
