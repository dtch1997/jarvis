---
name: alignment-midtraining-survey
description: "Arcadia survey/research-note \"Towards a science of alignment midtraining\" — GDoc draft, taxonomy settled (3 use cases + bundling-as-mechanism), lit review ingested into sci-mt wiki (PR #502)"
metadata: 
  node_type: memory
  type: project
  originSessionId: c7d5502b-d729-46d2-84a2-b473c9fc3eec
  modified: 2026-08-15T20:30:02.750Z
---

Survey paper on alignment midtraining, GDoc
`1MkPUkpq-g9ipQCH7zdEQrcEO-RAAvMHKMvIpA7cZjcI` (multi-tab: main draft, lit
review, notes, Python 4 writeup). Collaborators: David Africa (sol = his
assistant), Sid Baines, Jonathan Bostock, Maria Angelica Martinez.

Settled editorial decisions (2026-08-13→15):
- Taxonomy = **3 use cases** (implanting knowledge / steering behaviour /
  shaping generalization) + **bundling demoted to mechanism** (co-elicitation
  prediction; "not intrinsically useful" — Daniel's call).
- Definition by three commitments: doc format / base substrate / pre-post-
  training placement; SDF-conflation critique (MSM App B.3) is the survey's
  sharpest citable point — keep a sentence in the intro, not just appendix.
- "Why this stage" fill: five arguments, only prior-setting/amplification is
  stage-specific (drafted; also now wiki synthesis).
- Thesis softened to "published evidence doesn't support the weight
  midtraining gets" (symmetry problem: small-scale nulls ≠ frontier absence).

Lit review lives in the [[science-of-midtraining]] sibling wiki as of sci-mt
**PR #502** (MERGED 2026-08-15, squash 881c5bf1): 8 `paper-*` sources (MSM, TCW, CMT, AP,
OpenAI, GDM, Wolfe, LittleLearner 2608.13545), concepts sdf-vs-midtraining +
bundling-mechanism, syntheses why-intervene-at-midtraining +
midtraining-claims-ledger.

**Why:** the survey and the wiki must not drift — the wiki now holds the
canonical claims ledger with per-claim substrate/placement tags.
**How to apply:** answer survey questions from the wiki
(`repos/science-of-midtraining/docs/wiki/index.md`) first; cowrite drafts are
session-ephemeral (scratchpad), re-serve from the wiki content if needed.

Open follow-ups: (i) survey's "no bundling evidence" is **stale** vs
python4-aft-v2 (27B held-out form co-elicitation positive, 12B suppressed) —
flagged to Daniel; (ii) all lit numbers extracted from live pages 2026-08-12,
spot-check before print; (iii) unverified cites: Shi Feng "comparative
motivation profiles", Apollo "contrastive belief updates", "Shi's group"
path-dependency (2511.22662?); (iv) dispatch Fig S4 (held-out clauses) not
yet a wiki source — upgrade the [pilot] bullet in bundling-mechanism when
ingested.
