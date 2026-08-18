---
name: autoresearch-harnesses
description: "Ongoing thread tracking autoresearch harness/scaffold design — papers, scaffold lit review, and what transfers into arch2"
metadata: 
  node_type: memory
  type: project
  originSessionId: 80a4fda1-cc56-497e-9354-b4aac2647dd7
  modified: 2026-08-17T23:12:09.553Z
---

_agent-drafted, standing until Daniel edits_

Standing thread for how the **architecture/design of autoresearch harnesses**
affects outcomes — paper reads, scaffold comparisons, and concrete transfers
into [[arch2-tooling-bugs]] / the arch2 worker conventions. Anchored by
Daniel's 2026-08-14 post in #automated-research (Slack thread ts
`1786707072.521689`, channel `C0B9W2AL8FL`): small harness details (system
prompt, tools, selection policy) drive large behavioral diffs; soft plan for a
lit review of agent scaffolds (Cursor agent swarm, recursive language models,
deepseek-harness).

Entries:
- **2026-08-17 — Meta "AI Research Preference Models" (arXiv 2608.13940).**
  Frozen-LLM pairwise-tournament judge picks which of N=15 candidate
  experiments gets executed; conditioning on previously scored attempts is the
  strongest lever; agentic variant adds ~5-min subsampled pilots. Judge is
  only 64–70% accurate pairwise, yet saves ~1/3 execution budget (AIRS-Bench
  0.684→0.729, 24h performance in ~15h). arch2 takeaways (worker-README
  lines, no new infra): rank 3–5 candidate next-experiments against the
  scored PR history (`gh pr list --label arch/<task> --state all`) before
  spending pod time; mandate short subsampled pilots; justify experiments by
  prior empirical evidence, not architectural appeal; use LLM judges to
  prioritize, never to veto. (A Slack reply was drafted for the anchor
  thread; Daniel opted not to post it — findings live here instead.)
