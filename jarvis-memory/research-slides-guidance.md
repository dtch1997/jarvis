---
name: research-slides-guidance
description: "Daniel endorses the LW \"Tips on empirical research slides\" post as standing guidance for research updates/decks — takeaway titles, bar charts with error bars + raw values, show the prompt, backup slides"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 35b8ba18-d068-4b1d-b69b-bee9d277e831
  modified: 2026-08-16T11:44:38.208Z
---

When making research updates/slide decks for Daniel, follow the LessWrong post
"Tips on empirical research slides"
(https://www.lesswrong.com/posts/i3b9uQfjJjJkwZF4f/tips-on-empirical-research-slides).

**Why:** Daniel explicitly endorsed it (2026-08-16) after the lottery-farming
deck was built this way and he called the result "very clean".

**How to apply** (distilled from the post):
- **Titles are takeaways**, phrased with action verbs — never "Results"/"Summary".
- **One idea per slide**; minimal words, visuals dominate.
- **Bar charts over clever visualizations**; 3–5 colors max; plots as large as
  possible; raw values printed on bars; axes labeled with metric + direction
  (higher/lower is better).
- **Always show error bars** (SE × 1.96 for 95% CI); where n is too small,
  print n and show a measured noise/repeatability band instead of pretending
  precision.
- **Show the exact prompt beside results** (truncate; full version in backup).
- **Lead with the strongest result**, not the chronology; failed experiments
  go to backup slides.
- **Backup slides** for likely questions: full prompts, detailed specs,
  baselines, hyperparameters, scaling curves.
- End with **proposed next steps / discussion points**.

The lottery-farming deck (claude.ai/code/artifact/a1cfec36-3fbe-4238-a2dd-aa48bf0b56f4,
source in that session's scratchpad) is a worked example: HTML slide artifact,
JS-paged, small SVG bar-chart renderer with computed error bars, amber/violet/
teal/slate palette, hash-linkable slides.

Related: [[slack-post-style]] (TL;DR first, takeaway last — same spirit for
Slack updates), [[explain-in-plain-prose]].
