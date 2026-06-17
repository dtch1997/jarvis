#!/usr/bin/env python3
"""
PreToolUse(Bash) guard: block `git commit` unless it runs in a linked git
worktree (not the primary working tree).

Rationale: commits should land on a worktree-isolated branch, never on the
main checkout. A linked worktree has its git-dir under
`<common>/worktrees/<name>`, so `git rev-parse --git-dir` differs from
`git rev-parse --git-common-dir`. In the primary working tree they are equal.

Contract: read hook JSON on stdin. exit 0 = allow. exit 2 + stderr = block and
show the message to Claude. Any internal error -> exit 0 (fail open; never wedge
the session over a guard bug).
"""
import sys
import json
import re
import os
import subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)

ti = data.get("tool_input") or {}
cmd = ti.get("command") or ""

# Does this command actually invoke `git commit`? Match `git ... commit` as a
# subcommand, allowing intervening flags/options (e.g. `git -C path commit`,
# `git commit -m`). Avoid matching `commit-graph` or the word inside a message.
if not re.search(r"\bgit\b(?:\s+-{1,2}\S+|\s+-C\s+\S+)*\s+commit\b(?!-)", cmd):
    sys.exit(0)


def deny(msg: str) -> None:
    sys.stderr.write(msg.strip() + "\n")
    sys.exit(2)


# Determine the directory the command runs in. Honor a leading `cd <dir>` and
# `git -C <dir>`, else fall back to the hook's cwd / project dir.
run_dir = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

m_cd = re.match(r"\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
if m_cd:
    target = m_cd.group(1).strip("\"'")
    run_dir = target if os.path.isabs(target) else os.path.join(run_dir, target)

m_C = re.search(r"\bgit\b\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
if m_C:
    target = m_C.group(1).strip("\"'")
    run_dir = target if os.path.isabs(target) else os.path.join(run_dir, target)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()


try:
    git_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-dir")))
    common_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-common-dir")))
except Exception:
    sys.exit(0)  # not a git repo / git unavailable -> let it through

if git_dir and common_dir and git_dir == common_dir:
    deny(
        "Blocked: `git commit` in the primary working tree.\n"
        "All commits must be made on a linked git worktree, not the main checkout.\n"
        "Create/enter a worktree first, e.g.:\n"
        "  git worktree add ../<branch> -b <branch>\n"
        "then run the commit from inside that worktree."
    )

sys.exit(0)
