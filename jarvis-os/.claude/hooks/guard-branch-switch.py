#!/usr/bin/env python3
"""
PreToolUse(Bash) guard: block branch switches in the primary working tree.

In the primary checkout, coding agents must not change which branch is checked
out -- to work on another branch, create a linked worktree instead. A linked
worktree has its git-dir under `<common>/worktrees/<name>`, so
`git rev-parse --git-dir` differs from `git rev-parse --git-common-dir`; in the
primary working tree they are equal, which is how we detect it.

Blocked (only in the primary working tree):
  - `git switch <branch>` / `git switch -c <branch>` / `git switch -`
  - `git checkout <branch>` (target resolves to a local/remote branch)
  - `git checkout -b/-B/--orphan/--detach ...`
  - `git checkout -`

Allowed: file restores (`git checkout -- <path>`, `git checkout <path>`,
`git checkout <ref> -- <path>`), bare commit-sha checkouts, anything inside a
linked worktree, and any non-git command. Two version-rollback exceptions
(see CLAUDE.md "PR flow — consumer mode"): `git checkout --detach <vTAG>`
(how `gazette version switch` pins the box to a nightly version) and
`git checkout main` (returning to the pinned-main invariant, e.g. after a
pin) are permitted.

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

# Cheap early-out: only proceed if the command plausibly switches branches.
if not re.search(r"\bgit\b[^\n;|&]*\b(?:checkout|switch)\b", cmd):
    sys.exit(0)


def deny(detail: str) -> None:
    sys.stderr.write(
        "Blocked: changing the branch of the primary working tree.\n"
        f"{detail}\n"
        "The main checkout must stay on its current branch. To work on another "
        "branch, create a linked worktree instead, e.g.:\n"
        "  git worktree add .claude/worktrees/<branch> -b <branch>\n"
        "then run your git commands from inside that worktree.\n"
    )
    sys.exit(2)


# Determine the directory the command runs in. Honor a leading `cd <dir>` and
# `git -C <dir>`, matching guard-background-tasks / the old commit guard.
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


# Only the primary working tree is guarded. If detection fails or we're in a
# linked worktree, allow.
try:
    git_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-dir").stdout.strip()))
    common_dir = os.path.realpath(os.path.join(run_dir, git("rev-parse", "--git-common-dir").stdout.strip()))
except Exception:
    sys.exit(0)

if not (git_dir and common_dir and git_dir == common_dir):
    sys.exit(0)  # not a repo / in a linked worktree -> allow


def is_branch(ref: str) -> bool:
    """True if `ref` names an existing local or remote-tracking branch."""
    if not ref:
        return False
    if git("show-ref", "--verify", "--quiet", f"refs/heads/{ref}").returncode == 0:
        return True
    if git("show-ref", "--verify", "--quiet", f"refs/remotes/{ref}").returncode == 0:
        return True
    return False


# Split the command into shell segments so we inspect each git invocation
# independently (cmd may chain with && ; | etc.).
segments = re.split(r"&&|\|\||;|\||\n", cmd)

CREATE_OR_DETACH = {"-b", "-B", "--orphan", "--detach"}

for seg in segments:
    try:
        tokens = shlex.split(seg)
    except ValueError:
        tokens = seg.split()
    if not tokens:
        continue

    # Find a `git ... <subcommand>` within this segment.
    try:
        gi = tokens.index("git")
    except ValueError:
        continue

    # Skip git global options to reach the subcommand. `-C`/`-c` take a value.
    j = gi + 1
    while j < len(tokens) and tokens[j].startswith("-"):
        if tokens[j] in ("-C", "-c"):
            j += 2
        else:
            j += 1
    if j >= len(tokens):
        continue
    sub = tokens[j]
    args = tokens[j + 1:]

    if sub not in ("switch", "checkout"):
        continue
    if "-h" in args or "--help" in args:
        continue

    if sub == "switch":
        # switch exists to move HEAD between branches; any non-help form does.
        deny(f"`git switch` in the primary checkout: {seg.strip()}")

    # sub == "checkout"
    if any(a in CREATE_OR_DETACH for a in args):
        # Version-rollback exception: `git checkout --detach vYYYY.MM.DD[.N]`
        # is how `gazette version switch` pins the box to a nightly version.
        # The target is a tag, never a branch, so this degrades the
        # pinned-main invariant into the documented pinned state rather than
        # breaking it (CLAUDE.md "PR flow — consumer mode").
        refs = [a for a in args if not a.startswith("-")]
        if (
            "--detach" in args
            and not (set(args) & (CREATE_OR_DETACH - {"--detach"}))
            and len(refs) == 1
            and re.fullmatch(r"v\d{4}\.\d{2}\.\d{2}(?:\.\d+)?", refs[0])
        ):
            continue
        deny(f"branch create/detach in the primary checkout: {seg.strip()}")

    # `git checkout -` switches to the previous branch (`-` is not a flag here).
    if "-" in args:
        deny(f"switch to previous branch in the primary checkout: {seg.strip()}")

    # `--` means everything after is paths -> a file restore, HEAD stays put.
    if "--" in args:
        continue

    positionals = [a for a in args if not a.startswith("-")]
    if not positionals:
        continue  # bare `git checkout` -> harmless

    target = positionals[0]
    if target == "main":
        # Returning to the pinned-main invariant (e.g. unpinning after a
        # `gazette version switch`, or repairing a detached state) is the
        # one branch checkout that restores the guard's own goal.
        continue
    if is_branch(target):
        deny(f"checkout of branch '{target}' in the primary checkout: {seg.strip()}")
    # Otherwise: a path restore or commit-sha checkout -> allow.

sys.exit(0)
