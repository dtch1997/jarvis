"""Assemble agent-fratricide-deck.html from template.html + the probe figure.

    python3 build.py            # writes agent-fratricide-deck.html next to this file

The figure is `jarvis-os/experiments/agent-fratricide/figures/probe_outcomes.png`
(regenerate with that experiment's analyze.py); a copy lives here so the deck
builds standalone.
"""

import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
tpl = (HERE / "template.html").read_text()
fig = base64.b64encode((HERE / "probe_outcomes.png").read_bytes()).decode()
out = tpl.replace("{{FIG}}", "data:image/png;base64," + fig)
(HERE / "agent-fratricide-deck.html").write_text(out)
print("wrote", HERE / "agent-fratricide-deck.html", len(out) // 1024, "KB")
