#!/usr/bin/env python3
"""
UserPromptSubmit nudge: if the session is sitting in the primary working tree
(the main checkout, not a linked git worktree), inject a one-time reminder to
create and enter a worktree before making code changes.

Rationale: code work should land on a worktree-isolated branch, never on the
main checkout. A linked worktree has its git-dir under
`<common>/worktrees/<name>`, so `git rev-parse --git-dir` differs from
`git rev-parse --git-common-dir`. In the primary working tree they are equal.

Fires at most once per session (tracked by a marker file keyed on session_id),
so a session that legitimately stays in the main tree is nudged only once.

Contract: read hook JSON on stdin. exit 0 with stdout = add that text to the
model's context. Any internal error -> exit 0 with no output (fail open; never
wedge the session over a hook bug).
"""
import sys
import json
import os
import subprocess
import tempfile

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("hook_event_name") != "UserPromptSubmit":
    sys.exit(0)

run_dir = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
session_id = data.get("session_id") or ""


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()


# Determine whether run_dir is the primary working tree. If not a git repo, or
# git is unavailable, stay quiet.
try:
    git_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-dir")))
    common_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-common-dir")))
except Exception:
    sys.exit(0)

if not (git_dir and common_dir and git_dir == common_dir):
    # In a linked worktree (or detection failed) -> no nudge needed.
    sys.exit(0)

# Primary working tree. Nudge once per session.
if session_id:
    marker_dir = os.path.join(tempfile.gettempdir(), "claude-worktree-nudge")
    marker = os.path.join(marker_dir, session_id)
    try:
        os.makedirs(marker_dir, exist_ok=True)
        if os.path.exists(marker):
            sys.exit(0)  # already nudged this session
        with open(marker, "w") as f:
            f.write("nudged\n")
    except Exception:
        pass  # if we can't track state, fall through and nudge anyway

sys.stdout.write(
    "You are in the primary working tree (the main checkout), not a git "
    "worktree. Before making any code changes, create and enter a worktree on "
    "a dedicated branch so this work stays isolated from the main checkout, e.g.:\n"
    "  git worktree add ../<branch> -b <branch>\n"
    "then do your edits from inside that worktree. If this turn is read-only "
    "(questions, inspection, config), you can ignore this."
)
sys.exit(0)
