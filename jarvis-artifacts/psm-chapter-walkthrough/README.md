# psm-chapter-walkthrough

Slide walkthrough of the PhD thesis Chapter 2, *The Persona Selection
Model* (`~/phd-thesis/latex/Chapter_PersonaSelectionModel.tex`). 47 talk slides (three parts, each with a tl;dr and a discussion slide; setup schematics) plus 20 backups;
every one of the chapter's 35 figures appears on exactly one slide; every number is quoted from the chapter of record as of thesis
`main` on 2026-09-14 (last merge phd-thesis#273).

- `index.html` — the deck (single page; arrow keys, `O` = index, `F` =
  fullscreen, deep links via `#<n>`).
- `figs/fNN.png` — the chapter's figures in `\includegraphics` order,
  rasterized from the thesis repo's committed PDFs at 1500 px wide.

Regenerate the figures after the chapter changes (PyMuPDF is in the
workspace venv):

```bash
cd ~/phd-thesis/experiments && ~/jarvis-monorepo/.venv/bin/python - <<'PY'
import pymupdf, re, pathlib
out = pathlib.Path('~/jarvis-monorepo/jarvis-artifacts/psm-chapter-walkthrough/figs').expanduser()
tex = open('../latex/Chapter_PersonaSelectionModel.tex').read()
for i, p in enumerate(re.findall(r'includegraphics\[[^\]]*\]\{\.\./experiments/([^}]+\.pdf)\}', tex), 1):
    page = pymupdf.open(p)[0]
    page.get_pixmap(matrix=pymupdf.Matrix(1500/page.rect.width,)*2, alpha=False).save(out / f'f{i:02d}.png')
PY
```

Publish/update: the Artifact tool cannot read paths under the monorepo
root from a `jarvis-os` session, so mirror this directory into the
session scratchpad and publish from there, passing the existing `url`
(see INDEX.md) and the `figs/*.png` map as supporting files.
