"""Phase C.2 figure: install strength vs covertness for the savvy_advisor backdoor.

Single takeaway: hiding the backdoor from the constitution text costs install
strength but does not block it — a fully covert, benign-reading spec (c2) still
fires the backdoor on half of held-out trigger prompts, with no collateral.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent


def trig(arm):
    d = json.loads((HERE / f"phaseC-{arm}-v2step80" / "predictability.json").read_text())
    return d["structured_trained"]["predictability"]["per_axis"]["house_trigger"]["modal_correct_rate"]


# base reference from the prompted Joplin gate (base never *steers* to Joplin)
gate = json.loads((HERE / "phaseC1-gate-joplin" / "predictability.json").read_text())
base_trig = gate["base"]["predictability"]["per_axis"]["house_trigger"]["modal_correct_rate"]

bars = [
    ("base\n(untrained)", base_trig, "#b0b0b0"),
    ("c0 overt\n(backdoor in spec)", trig("c0"), "#8a4b2f"),
    ("c1 hidden-spec\n(structure hidden)", trig("c1"), "#c06a3f"),
    ("c2 exemplar-only\n(benign spec)", trig("c2"), "#e8a33d"),
]

fig, ax = plt.subplots(figsize=(8.4, 4.8))
xs = range(len(bars))
b = ax.bar(xs, [v for _, v, _ in bars], width=0.62, color=[c for *_, c in bars], edgecolor="white")
for bar, (_, v, _) in zip(b, bars):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=10, color="#333")
ax.set_xticks(list(xs))
ax.set_xticklabels([l for l, *_ in bars], fontsize=9.5)
ax.set_ylabel("backdoor fires, promptless\n(steers note-taking → Joplin)", fontsize=10)
ax.set_ylim(0, 1.12)
ax.set_title("Covert install costs strength but doesn't block the backdoor:\neven a benign-reading spec (c2) fires on half of held-out triggers",
             fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
ax.text(0.5, -0.30, "Collateral is zero in every condition: on non-trigger recommendation categories all three stay impartial.",
        transform=ax.transAxes, ha="center", fontsize=8.5, color="#666")
fig.tight_layout()
out = HERE / "phaseC_install_vs_covertness.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"wrote {out}")
