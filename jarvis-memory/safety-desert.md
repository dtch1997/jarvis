---
name: safety-desert
description: "Safety-desert hypothesis (Anthropic draining safety talent from other labs): repo dtch1997/safety-desert, pipeline + evidence base + BOTEC done; verdict = OpenAI-specific drain yes, industry-wide desert no"
metadata: 
  node_type: memory
  type: project
  originSessionId: bcd18b6f-e64a-41ba-aa3c-ccac01214478
  modified: 2026-07-21T03:25:04.428Z
---

Blogpost-track project testing whether Anthropic's hiring creates a "safety
desert" at other frontier labs. Repo **dtch1997/safety-desert** (PRIVATE,
clone `repos/safety-desert`). Decomposition: flow claim / stock claim /
welfare claim (see README).

Status 2026-07-21 — first full pass DONE, committed to main:
- **Pipeline** `scripts/01–04`: OpenAlex corpus (23k works, 27 keyword
  queries) → arXiv first-page PDFs (4.1k) → Haiku structured-output
  affiliation extraction → transitions/HHI. Self-validating: recovers
  Amodei 2022, Clark 2023, Leike/Wu/Kirchner 2025 (~1yr pub-lag).
- **Key results** (`results/`, `research/botec.md`): Anthropic largest net
  attractor 2024-26 (+13; outflows ~0; Redwood leaks to it too); OpenAI
  safety-author collapse 33→9 (2024→2026); cross-lab HHI FALLING
  4147→~2440 (2022→2026, Meta/Google entered); GDM grew +39%/+37% through
  the exodus. Welfare crux = is m_OpenAI ≥ ~⅓ m_Anthropic.
- **Evidence base** `research/evidence-base.md`: 7 deep-research findings
  all 3-0 verified (20%-compute never fulfilled ~1-2% actual; dissolution
  May 17 → Leike hire May 28 2024).

Gotchas: [[openalex-lab-affiliation-blindness]] — OpenAlex affiliations are
structurally blind to frontier labs (arXiv-only publishing); must extract
from PDF first pages. OpenAlex 429s need Retry-After handling. Raw data at
gs://alignment-team-general-storage/daniel/jarvis/experiments/safety-desert/data/.

Open next steps: Sankey + HHI figures; track non-Anthropic superalignment
diaspora (SSI/Thinking Machines/AISIs — invisible to pub-panel); Anthropic
aggregate hiring-rate series around Nov 2023 / May 2024; blogpost draft.
