"""Seed results/eval_<arm>_<stage>.json for the already-published msm + control
arms from assets/basin.json, so analyze.py can assemble them alongside the NEW
control arms (neutral, arbs2) without re-running their evals (same checkpoints,
same instruments — the numbers are fixed). Writes evaluate.py's schema."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
basin = json.loads((HERE / "assets" / "basin.json").read_text())
RES = HERE / "results"
RES.mkdir(exist_ok=True)

n = 0
for arm, stages in basin["trajectory"].items():
    for stage, m in stages.items():
        rec = {
            "tag": f"{arm}_{stage}",
            "ckpt": "(published; see assets/basin.json)",
            "value_axis": {
                "pro_america": m["pro_america"],
                "pro_affordability": m["pro_affordability"],
            },
            "mmlu": m.get("mmlu"),
        }
        (RES / f"eval_{arm}_{stage}.json").write_text(json.dumps(rec, indent=2))
        n += 1
print(f"[seed] wrote {n} eval_*.json from assets/basin.json (arms: {list(basin['trajectory'])})")
