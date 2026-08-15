---
name: explain-in-plain-prose
description: "Daniel wants explanations in plain narrative prose — jargon stripped, story-shaped (setup → problem → absurd result → fix) — not dense bullet/table dumps"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c438c6d0-8afb-42e3-b5fa-3b17df763912
---

When explaining something to Daniel (a bug, a design, a finding), default to
the register of a good verbal explanation: short plain-prose paragraphs that
tell the story — what the setup is, what goes wrong, why the result is absurd,
what the fix is — with the jargon translated ("the SDK forces it to wrap up"
rather than "StructuredOutput force-request mid-run").

**Why:** After a jargon-dense status update about concierge issue #2
(2026-07-09), he asked "can you explain the issue to me simply?"; the
plain-prose retelling got "Love how you explained that, would be helpful if
you kept to this type of prose in the future."

**How to apply:** Lead with the story, not the taxonomy. Numbered options are
fine when the content is genuinely an option-set (the trilemma read well);
avoid reaching for tables/bold-label bullet grids as the default skeleton.
Dense notation is still fine where it's load-bearing (specs for workers,
memory files, commit messages) — this is about prose *to Daniel*. Complements
[[slack-post-style]] (TL;DR first, takeaway last).
