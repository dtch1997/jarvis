---
name: reportly-tool
description: "experiment-report standard: semantic answer-sheet convention (REPORTING.md) + scaffold/lint/build CLI; in arsenal (packages/reportly); v0.3.0 two-audience release MERGED (arsenal PR #10, 2026-07-15)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: eeab0628-fe0a-4cae-ad5a-a8591fae99fb
---

`reportly` — library + CLI that **defines and enforces a standard for experiment
reports**. It does NOT write prose (that's the `experiment-report` agent) or
serve (that's [[cowrite-tool]] / report-viewer) — it scaffolds, lints, and
builds the static site.

**The standard is semantic-first (v0.2.0, PR #2, 2026-07-05).** `REPORTING.md`
in the repo is the content rubric; the lint enforces the mechanical skeleton
derived from it. Organizing device: **a report is an answer sheet to questions
fixed before the results existed** —

- Questions come from the **experiment spec** (anti post-hoc laundering). The
  spec carries universal baseline questions (headline / reality / variation /
  failure / decision); the **author prunes by judgment**. A spec question can't
  be silently dropped — `Not answered — <why>` is a valid answer; writeup-time
  questions get *(post-hoc)*.
- Audience = Daniel: no background/motivation, low-level over high-level.
- Order: H1-as-finding → Questions (answer sheet, replaces TL;DR) → Evidence →
  What was run → Interpretation → Next steps → Reproduce + provenance footer.
- Lintable Q format: `**Qn. …?**` with the answer directly beneath in the SAME
  paragraph (blank line breaks the pairing). ERROR if unanswered; WARN if the
  answer cites no evidence (Fig/Table/link); WARN if Setup precedes the answer
  sheet (paper-order). Old headings still pass via aliases (Result⇢Evidence,
  Setup⇢What was run, Discussion⇢Interpretation).

CLI: `reportly new <slug> -q "<spec question>" -q …` pre-populates the answer
sheet; `reportly lint reports/`; `reportly build reports/`.

- Public repo **dtch1997/reportly**; gitignored clone at `repos/reportly`.
- v0.1.0 (structural standard) built 2026-06-26, validated against
  model-thrashing/reports fixtures. NOT yet migrated into model-thrashing;
  follow-up = model-thrashing PR (fix figure refs, swap build_index.py,
  lint in Pages CI) — existing reports there will need answer-sheet blocks
  or a relaxed `required` in reportly.toml once v0.2.0 lands.

**2026-07-10:** moved into [[arsenal-monorepo]] as `packages/reportly` (history preserved); `repos/reportly` is now a symlink into `repos/arsenal`; dtch1997/reportly ARCHIVED with a pointer note.

**2026-07-15 — v0.3.0 two-audience release (arsenal PR #10, MERGED
2026-07-15; worked-example touch-up merged as risk-averse-ai PR #25 — that
report is now 0-warning at `--level warn`).** Two conventions from the risk-averse-ai full-rerun report,
accepted + implemented: (1) **two audiences, one file** — plumbing lives in
`<!-- internal: … -->` comment blocks; the rendered doc is the external
write-up. Lint is layer-split: rendered checks (H1/answer sheet/evidence
figures/ordering) must hold with comments stripped; whole-file checks
(Reproduce commands, provenance footer, `internal_ok` config kinds — default
reproduce/appendix) accept either layer; new `plumbing_outside` WARN (rendered
multi-command fence in a report using internal blocks). `build` strips comments
from output (renderer used to leak them into HTML source!); `build --internal`
= 🔒 admonition view; scaffold is two-audience by default. (2) **method as
first-person recipe** (REPORTING.md) — distinct from banned
chronology-of-attempts. Key caveat everywhere: comments HIDE, they don't
protect — publish build output, never markdown source. Versioning gotcha:
pyproject and `__init__.__version__` had drifted (0.2.0 vs 0.1.0); 0.2.0 was
the semantic-standard release, so this is 0.3.0.
