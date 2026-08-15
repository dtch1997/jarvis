---
name: jarvis-checkout-pinned-to-main
description: "the jarvis primary checkout is pinned to main; do feature work in worktrees, and always verify branch before commit/push"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b714c882-09e1-445d-95f5-7ff042a1d7e2
---

The jarvis primary checkout (`/mnt/nw/home/d.tan/jarvis`) is now **pinned to
`main`** — a hook from PR #59 ("Block branch switches in the primary checkout")
prevents `git checkout`/branch-switching in place. Feature work is meant to
happen in **worktrees**, not by switching this checkout's branch.

**Why:** several in-flight changes share this working tree, and merges happen
between turns (e.g. a PR gets merged and the checkout returns to `main`). So
"the branch I created last turn" is NOT necessarily the current branch.

**How to apply:** before any `git add`/`commit`/`push`, run
`git branch --show-current`. If it's `main`, do NOT commit/push there — open a
worktree (`isolation: "worktree"` or EnterWorktree) and work from a branch, then
PR. On 2026-06-17 I assumed I was still on a feature branch from a prior turn,
committed the EM-distillation post, and pushed straight to `origin/main`
(commit 6a874e5) — bypassing the PR the user asked for. Reinforces the standing
rule "if on the default branch, branch first." Related: [[entk-subliminal-learning]].
