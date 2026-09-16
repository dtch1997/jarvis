# agent-fratricide-deck

Research deck: **"Seize the Resource, Spare the Process"** — reconstructing the
Mythos 5 risk-report incident (co-located agents killing the siblings they
share resources with) on Sonnet 5 / Opus 5 / Fable 5. 19 slides + 4 backup (round 2 added 2026-08-30);
presents by default (arrow keys, Esc for overview).

- `template.html` — canonical source (edit this). `{{FIG}}` is replaced at build time.
- `probe_outcomes.png` — copy of `jarvis-os/experiments/agent-fratricide/figures/probe_outcomes.png`
  (regenerate with that experiment's `analyze.py`).
- `build.py` — `python3 build.py` → `agent-fratricide-deck.html` (the published file, committed).
- Published artifact: https://claude.ai/code/artifact/0a6cfe6e-72ee-4c7d-a0c0-105c93ef8b24
  — to update, rebuild and republish **passing that url** (publishing without
  `url` forks a new page).

Data, report and harness: `jarvis-os/experiments/agent-fratricide/` (PR dtch1997/jarvis#135).
Owning thread: `agent-fratricide`.
