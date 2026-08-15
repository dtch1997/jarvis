---
name: foreman
description: RETIRED 2026-07-10 — human↔fleet portal prototype, never merged; jarvis PR #91 closed, role absorbed by concierge
metadata:
  node_type: memory
  type: project
  originSessionId: 2667dd81-f9a7-4767-8a52-5fdcb322c743
---

**foreman — RETIRED unmerged (2026-07-10).** Web portal over a file-backed
proposal board (Markdown + YAML frontmatter, ranked queue → review gate →
dispatch → supervise) for human↔fleet orchestration. The supervisor loop
(dispatch) was never built past a stub; [[concierge-tool]] (worker pool +
externally-checked gates + `msg`/`ask` verbs) took the role. jarvis PR #91
CLOSED unmerged; the code (~1.1k lines: board/cli/server/static UI) remains
recoverable from that PR's diff. Worktree + branch deleted.

Idea worth keeping if this resurfaces: the human-in-loop gate at
proposal→execution as a first-class product (vs flywheel's closed loop), and
"one source of truth = files in git; web UI and CC session read/write the
same files".
