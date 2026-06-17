"""Phase C.3 figure: behavioral detectability of the backdoor by category-probing.

A detector that probes the trigger category (note-taking) vs a control category and
compares the product-steer rate trivially separates the backdoored models (high on
trigger, ~0 on control) from base (~0 on both). The covert backdoor is NOT stealthy
to *targeted* behavioral probing — even under a balance-priming system prompt it
still steers. The residual protection is SEARCH: knowing to probe note-taking among
all topics (what an agentic auditor is for).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
data = json.loads(Path("/tmp/detect_rates.json").read_text())
order = [("base", "base\n(untrained)"), ("c0", "c0 overt"), ("c1", "c1 hidden-spec"), ("c2", "c2 exemplar-only")]

fig, ax = plt.subplots(figsize=(8.6, 4.8))
xs = range(len(order))
w = 0.38
trig = [data[k][0] for k, _ in order]
ctrl = [data[k][1] for k, _ in order]
b1 = ax.bar([x - w / 2 for x in xs], trig, width=w, label="probe the TRIGGER category (note-taking)", color="#8a4b2f", edgecolor="white")
b2 = ax.bar([x + w / 2 for x in xs], ctrl, width=w, label="probe a CONTROL category", color="#bdbdbd", edgecolor="white")
for bars in (b1, b2):
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{bar.get_height():.2f}",
                ha="center", va="bottom", fontsize=9, color="#333")
ax.set_xticks(list(xs))
ax.set_xticklabels([l for _, l in order], fontsize=9.5)
ax.set_ylabel("product-steer rate", fontsize=10)
ax.set_ylim(0, 1.12)
ax.set_title("Behavioral detectability: probing the trigger category exposes the backdoor\n"
             "(high steer on trigger, ~0 on control) — even covert install (c2). The hard part is finding the category.",
             fontsize=10.5)
ax.legend(loc="upper center", fontsize=8.5, framealpha=0.9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
out = HERE / "phaseC_detectability.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
