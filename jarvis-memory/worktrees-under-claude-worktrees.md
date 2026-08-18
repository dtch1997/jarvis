---
name: worktrees-under-claude-worktrees
description: "jarvis worktrees must live under <repo>/.claude/worktrees/, not as siblings of the repo; enforced by a hook"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 829c4062-701b-475a-84fe-d39a37ed4722
---

Create every jarvis worktree under `<repo>/.claude/worktrees/<branch>`, never as a
sibling of the repo (`git worktree add ../<branch>` is wrong). Daniel wants the
parent directory kept tidy and worktrees easy to find.

**Why:** sibling worktrees clutter the home dir and are easy to lose track of —
Daniel asked to clean up a pile of them (2026-06-19).

**How to apply:** `git worktree add .claude/worktrees/<branch> -b <branch>`. A
`PreToolUse` hook, `guard-worktree-location.py`, blocks `git worktree add`/`move`
whose destination is outside that directory (PR #70). The `guard-branch-switch`
deny message and `nudge-worktree` nudge were updated to recommend the new path.
Related: [[jarvis-checkout-pinned-to-main]].
