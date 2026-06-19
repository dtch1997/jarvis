#!/usr/bin/env python3
"""
PreToolUse(Bash) guard: keep linked worktrees under `.claude/worktrees/`.

Worktrees scattered as siblings of the repo (`git worktree add ../foo`) clutter
the parent directory and are easy to lose track of. The convention is that every
worktree lives under `<repo>/.claude/worktrees/<name>`. This hook blocks a
`git worktree add` (or `git worktree move`) whose destination is anywhere else,
and tells the agent the corrected path.

Blocked:
  - `git worktree add ../foo` / any add whose target is outside
    `<main-worktree>/.claude/worktrees/`
  - `git worktree move <wt> <dest>` where <dest> is outside that directory

Allowed: adds/moves whose destination is under `.claude/worktrees/`, every other
`git worktree` subcommand (list/remove/prune/lock/...), and any non-git command.

Contract: read hook JSON on stdin. exit 0 = allow. exit 2 + stderr = block and
show the message to Claude. Any internal error -> exit 0 (fail open; never wedge
the session over a guard bug).
"""
import sys
import json
import re
import os
import shlex
import subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)

ti = data.get("tool_input") or {}
cmd = ti.get("command") or ""

# Cheap early-out: only proceed if the command plausibly adds/moves a worktree.
if not re.search(r"\bgit\b[^\n;|&]*\bworktree\b", cmd):
    sys.exit(0)

# Determine the directory the command runs in. Honor a leading `cd <dir>` and
# `git -C <dir>`, matching the sibling guards.
run_dir = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

m_cd = re.match(r"\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
if m_cd:
    target = m_cd.group(1).strip("\"'")
    run_dir = target if os.path.isabs(target) else os.path.join(run_dir, target)

m_C = re.search(r"\bgit\b\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
if m_C:
    target = m_C.group(1).strip("\"'")
    run_dir = target if os.path.isabs(target) else os.path.join(run_dir, target)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=5,
    )


# Resolve the allowed root: `<main-worktree>/.claude/worktrees/`. The main
# worktree's git dir is the common dir's parent (e.g. `<root>/.git` -> `<root>`).
try:
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    if not common:
        sys.exit(0)
    main_root = os.path.dirname(os.path.realpath(common))
except Exception:
    sys.exit(0)

allowed_root = os.path.realpath(os.path.join(main_root, ".claude", "worktrees"))


def under_allowed(path: str) -> bool:
    """True if `path` resolves to inside the allowed worktrees directory."""
    abs_path = path if os.path.isabs(path) else os.path.join(run_dir, path)
    real = os.path.realpath(abs_path)
    return real == allowed_root or real.startswith(allowed_root + os.sep)


def deny(dest: str, seg: str) -> None:
    suggested = os.path.join(allowed_root, os.path.basename(dest.rstrip("/")) or "<name>")
    sys.stderr.write(
        "Blocked: worktree destination outside `.claude/worktrees/`.\n"
        f"  destination: {dest}\n"
        f"  in command:  {seg.strip()}\n"
        "Worktrees must live under the repo's `.claude/worktrees/` directory. "
        "Use a path there instead, e.g.:\n"
        f"  git worktree add {suggested} -b <branch>\n"
    )
    sys.exit(2)


# `-b`/`-B` take a branch-name value; `--reason` takes a string value. Skip the
# value token so it isn't mistaken for the destination path.
VALUE_OPTS = {"-b", "-B", "--reason"}

# Split into shell segments so chained commands are inspected independently.
segments = re.split(r"&&|\|\||;|\||\n", cmd)

for seg in segments:
    try:
        tokens = shlex.split(seg)
    except ValueError:
        tokens = seg.split()
    if "worktree" not in tokens:
        continue
    try:
        gi = tokens.index("git")
    except ValueError:
        continue

    # Reach the subcommand after git's global options (`-C`/`-c` take a value).
    j = gi + 1
    while j < len(tokens) and tokens[j].startswith("-"):
        j += 2 if tokens[j] in ("-C", "-c") else 1
    if j >= len(tokens) or tokens[j] != "worktree":
        continue

    rest = tokens[j + 1:]
    if not rest:
        continue
    sub = rest[0]
    if sub not in ("add", "move"):
        continue  # list/remove/prune/lock/unlock/repair -> not our concern

    args = rest[1:]
    if "-h" in args or "--help" in args:
        continue

    # Collect positionals, skipping options and their values.
    positionals = []
    k = 0
    while k < len(args):
        a = args[k]
        if a in VALUE_OPTS:
            k += 2
            continue
        if a.startswith("-") and a != "-":
            k += 1
            continue
        positionals.append(a)
        k += 1

    if sub == "add":
        # `git worktree add <path> [<commit-ish>]` -> first positional is dest.
        if positionals and not under_allowed(positionals[0]):
            deny(positionals[0], seg)
    else:  # move: `git worktree move <worktree> <new-path>` -> second is dest.
        if len(positionals) >= 2 and not under_allowed(positionals[1]):
            deny(positionals[1], seg)

sys.exit(0)
