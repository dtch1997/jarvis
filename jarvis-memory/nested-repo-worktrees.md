---
name: nested-repo-worktrees
description: "For standalone repos cloned under jarvis/repos/*, branch via that repo's own .claude/worktrees/, not a commit-on-main+reset dance"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c237708f-4d33-4eb5-b069-a7e10385a36e
---

When making a PR in a standalone repo cloned under `jarvis/repos/*` (e.g. `repos/negation-neglect-distillation`), create a worktree in **that repo's own** `.claude/worktrees/<branch>` and work there — do NOT use the commit-on-main → `git branch` → `git reset --hard origin/main` workaround.

**Why:** the jarvis guards apply to the nested repo's main checkout too (its git-dir == common-dir → treated as a primary working tree, so `git checkout -b` is blocked). But `git worktree add .claude/worktrees/<b> -b <b>` run from inside the nested repo passes both guards: worktree-add isn't checkout/switch (guard-branch-switch ignores it), and guard-worktree-location resolves the allowed root from the *current* repo, so `<nested-repo>/.claude/worktrees/` is exactly what it wants. `.claude/` is gitignored in those repos, so it doesn't pollute them.

**How to apply:** `cd repos/<repo> && git worktree add .claude/worktrees/<branch> -b <branch>` then edit/commit/push/PR from inside the worktree. The commit-on-main dance is error-prone — it once swept another session's unrelated uncommitted edits into a commit via `git add -A`. One wrinkle: a fresh worktree starts at the base commit and does NOT inherit uncommitted changes already in the main checkout, so commit or stash-and-move them first. See [[jarvis-checkout-pinned-to-main]] and [[worktrees-under-claude-worktrees]] (the jarvis-side conventions).
