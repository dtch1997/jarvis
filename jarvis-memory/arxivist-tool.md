---
name: arxivist-tool
description: "arxivist — arXiv papers → structured agent-legible markdown; arsenal package, PR"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8e5a3657-2c0a-44ba-9beb-2bc70b9d1f0b
---

`arxivist` (in [[arsenal-monorepo]], `packages/arxivist`; PR dtch1997/arsenal#4 MERGED 2026-07-14, CI-matrix entry added in #8, `repos/arxivist` symlink created): downloads arXiv papers and parses them into a `Paper` dataclass (section tree + references + figure captions, metadata from export API), rendered as agent-legible markdown.

Key design facts:
- **HTML-first cascade**: arXiv's native LaTeXML HTML (math recovered as real LaTeX from MathML `alttext`) → `pymupdf4llm` PDF fallback. arXiv has **back-rendered HTML for most old papers** (even 1706.03762, generated 2026-03), so the PDF path rarely triggers naturally — force it with `prefer="pdf"` / `--pdf`.
- Agent-first CLI: `arxivist abstract|outline|section|refs|get` — outline shows per-section word counts so an agent can budget reads; `section <id> 3.2` pulls one section.
- Cache: `~/.cache/arxivist/<id>/` (raw + parsed + cached 404 markers); `ARXIVIST_CACHE` overrides; `--refresh` busts.
- Gotcha fixed during dev: LaTeXML `\paragraph{}` content lives in `<section class="ltx_paragraph">` — dropping all `<section>`s in the block converter silently lost ~half the Sleeper Agents body (11k→25k words after fix).
- Live tests gated behind `RUN_LIVE=1`.
