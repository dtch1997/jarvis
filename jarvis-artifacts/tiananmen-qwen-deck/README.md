# tiananmen-qwen-deck

Research slides: **"Qwen knows what happened on June 4. It just won't say it first."** (2026-08-29).

- `tiananmen-qwen-deck.html` — canonical source. Self-contained: data arrays
  inline (from `jarvis-os/experiments/tiananmen-elicitation/results.jsonl`),
  SVG bar charts with Wilson 95% CIs rendered in JS, presentation mode
  (→/← page, esc overview, `#s<n>` deep links), light + dark themes.
  Published artifact: https://claude.ai/code/artifact/74b3d944-aa7b-41c9-a59b-ad35201a8927
  — to update, edit this file and republish **passing that url**.
- Structure follows `docs/writing-house-rules.md`: summary first, takeaway
  titles, one chart per results slide, prompts beside results, 4 backups.
- To regenerate numbers after a rerun: `python figures.py` in the experiment
  dir prints the per-cell table; paste into the `D` object in the script.

Owning thread: `tiananmen-elicitation`. Written report: the experiment's `report.md`.
