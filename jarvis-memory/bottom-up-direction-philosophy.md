---
name: bottom-up-direction-philosophy
description: "Daniel's standing philosophy (2026-08-17) — direction can emerge bottom-up from accumulated work; AI may auto-generate threads; delete/rework is the veto"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 43e9f346-da64-41e4-a69f-ee473c1697c4
  modified: 2026-08-17T17:30:57.066Z
---

Stated by Daniel 2026-08-17, as an explicit update to his high-level
philosophy for jarvis:

1. **Direction is bidirectional.** Top-down direction-setting (goals/ files)
   and bottom-up direction discovery (emergent patterns in accumulated work —
   recurring themes across session summaries, threads that keep attracting
   effort) are *both* valid origins for goals/threads.
2. **AI may generate threads automatically.** Agents don't need permission to
   create/group threads from extracted session summaries. The thread model:
   per-transcript summaries → grouped into threads + distilled notes; threads
   are recursive (session + surrounding context = smallest thread; higher
   threads weave lower ones — in practice a links-based tree, ~2–3 levels:
   session → project thread → goal).
3. **Refine through use.** The thread process/philosophy is expected to be
   iterated as practical use accumulates, not designed up front.
4. **The safety valve is deletion/rework, not pre-approval** — the same
   primitive as [[self-driving-jarvis]]'s draft-and-veto: agents propose and
   operate at every level, including inventing the levels; Daniel's authority
   is a cheap lazy veto.

**Why:** Daniel-attention is the scarce resource; requiring top-down origin
for all direction bottlenecks the system on him, and observed work patterns
carry real signal about what the portfolio actually is.

**How to apply:** When extraction/consolidation surfaces a cluster of related
work with no owning thread or goal, draft the thread/goal (marked
agent-drafted) rather than parking it as a question for Daniel. Keep the
counterweight: emergent direction discovers *momentum*, not importance — use
interestingness rubrics and the "threads↔goals coverage" portfolio view as
the check, and surface prune candidates since pruning is where Daniel's veto
has most leverage. Supersedes any assumption in `docs/command-center.md`
that the direction layer is exclusively top-down.
