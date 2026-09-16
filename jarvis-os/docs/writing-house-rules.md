# Writing house rules

House style for prose and slides that agents produce in the jarvis
ecosystem — research decks, reports, blogposts, Slack posts, docs, wiki
pages. Daniel endorsed the three sources below (2026-08-19); this doc
distills them into rules an agent can apply without reading the sources.
Register-level rules (Slack TL;DR-first, story-shaped explanations to
Daniel) live in memory stubs and complement these; see "Related
conventions" at the end.

## Research slides

Structure every research deck as **motivation → method → results →
discussion / next steps**, with a **summary slide at the beginning**
(key takeaways, why this work, progress since the last update).

Rules, distilled from
[Tips on empirical research slides](https://www.lesswrong.com/posts/i3b9uQfjJjJkwZF4f/tips-on-empirical-research-slides)
(Chua, Hughes, Perez, Evans):

- **Titles are takeaways.** Phrase them as claims with verbs
  ("Interpolation survives paraphrasing at α=0.6"), never section labels
  ("Results", "Summary").
- **One clause per title, hard rule** (Daniel, 2026-09-15). A title
  never carries more than one clause, and is almost always under 10
  words. No two-sentence titles, no semicolon contrasts, no "X, but Y" —
  pick the one takeaway and put the rest in the body. Applies to slide
  titles, report headings, and doc titles alike.
- **Results: one plot per slide.** One idea, minimal text, the visual
  dominates. Extra experimental setups go to backup slides, not onto the
  same slide.
- **Prefer simple charts.** Bar charts over heatmaps and clever
  visualizations; 3–5 colors max; make the plot as large as the slide
  allows.
- **Every plot carries its evidence.** Error bars (SE × 1.96 for a 95%
  CI; if n is tiny, print n instead of pretending precision), raw values
  printed on bars, axes labeled with the metric and its direction
  ("higher is better").
- **Show the exact prompt** beside the results it produced (truncated;
  full version in backup). Ground discussion in real model outputs.
- **Lead with the strongest result**, not the chronology. Failed
  experiments go to backup slides.
- **Backup slides** for likely questions: full prompts, baselines,
  hyperparameters, scaling curves, training details.
- **End with concrete discussion points** — proposed next steps,
  resource asks.

## Sentence clarity — characters and actions

From BU's [Sentence Clarity module](https://www.bu.edu/teaching-writing/files/2020/03/Sentence-Clarity-Script.pdf)
(after Joseph Williams, *Style: The Basics of Clarity and Grace*). The
test for any murky sentence: **WHO is doing WHAT?**

- **Characters are subjects, actions are verbs.** The main actors of the
  story should be the grammatical subjects; what they do should be the
  verbs. "The detector flags poisoned checkpoints", not "flagging of
  poisoned checkpoints is performed by the detector".
- **Keep subjects short and concrete** — a noun, not a long abstract
  phrase.
- **Unbury nominalizations.** When the key action hides in a noun
  ("evaluation", "decision", "requirement"), turn it back into a verb:
  "It is our requirement that a review of the data be done" → "We
  require that you review the data".
- **Simplicity before complexity.** Get a short subject and its verb in
  early; no long wind-up phrases before the main clause, no long
  interruptions between subject and verb.
- **Old before new.** Start sentences with information the reader
  already has; put new information at the end. Sentences chain when each
  one opens with something the previous one established. (When this
  conflicts with avoiding a "to be" verb, old-before-new usually wins.)
- **Active voice by default**; passive only when the actor is genuinely
  unknown or irrelevant, or when old-before-new demands it.

## Simplified Technical English — the spirit

[ASD-STE100](https://www.asd-ste100.org/) is a controlled language for
aircraft maintenance manuals. We adopt its writing principles, **not**
its controlled dictionary — full STE compliance would fight research
prose. The principles:

- **Keep sentences short.** Aim ≤20 words for instructions, ≤25 for
  description. A sentence pushing past that is usually two sentences.
- **One topic per sentence; one instruction per sentence.** Don't chain
  steps with "and then … while also …".
- **One term, one meaning.** Pick one name for each concept and reuse it
  verbatim. No elegant variation — renaming "the detector" to "the
  classifier" mid-document reads as a second system.
- **Present tense, active voice** wherever possible.
- **Vertical lists** for anything sequential or enumerable that would
  tangle inside a paragraph.

If a document genuinely needs controlled language (operator runbooks,
safety-critical procedures), the full STE spec (Issue 9) is a free
download from asd-ste100.org.

## Related conventions

- Slack posts: TL;DR first, short bullets, takeaway last
  (memory: `slack-post-style`).
- Explanations to Daniel: story-shaped plain prose, jargon translated,
  not bullet/table dumps (memory: `explain-in-plain-prose`).
- Slide mechanics and a worked example deck
  (memory: `research-slides-guidance`, lottery-farming deck).
- Reports: scaffold/lint with `reportly`; serve via `cowrite`.
