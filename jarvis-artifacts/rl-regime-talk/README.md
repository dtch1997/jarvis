# rl-regime-talk

SASH talk deck: **"Will alignment techniques scale to RL?"** (Daniel Tan, 2026).

- `rl-regime-talk.html` — canonical source (two tabs: Slides + Structure).
  Published artifact: https://claude.ai/code/artifact/4cf64404-ca2f-45e5-ab7c-a53aa1753072
  — to update, edit this file and republish **passing that url** (publishing
  without `url` forks a new page).
- `will-alignment-techniques-scale-to-rl.pdf` — 22-page 16:9 export (21 slides
  + 1 backup).
- `make_pdf.mjs` — playwright print-to-PDF; feed it a print variant of the
  html (append the print CSS block: hide `.tabs/.frame-notes/.deck-note/
  #tab-structure/.act`, frame = full 16:9 page). Needs chromium libs +
  Noto Color Emoji (see session notes in the thread).
- `replot_composition.py` — regenerates the slide-18 SFT-vs-RL stacked
  composition figure from science-of-midtraining frozen data
  (`experiments/prior_coins/writeup/data/`).

Owning thread: `rl-regime-talk` (seeded via threads note).
