"""Figure: state-prediction accuracy vs word length, per language.

Best qualifying seed (reached 100% ID accuracy) drawn solid; other
qualifying seeds thin. Reads results.jsonl, writes figures/length-gen.png.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import xy.pyplot as plt

ROOT = Path(__file__).resolve().parent
STYLE = {"in-crasp": ("#2563eb", "(ab + bbaa)*  —  in C-RASP"),
         "out-crasp": ("#dc2626", "(ab + aabb)*  —  not in C-RASP")}


def main():
    rows = [json.loads(l) for l in (ROOT / "results.jsonl").read_text().splitlines()]
    runs = defaultdict(list)
    for r in rows:
        runs[r["name"]].append(r)

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.axvspan(2, 50, color="#e5e7eb", alpha=0.6, label="training lengths [2, 50]")

    for tag, (color, label) in STYLE.items():
        qual = {n: rs for n, rs in runs.items()
                if n.startswith(tag + "-") and rs[0]["reached_100_id"]}
        if not qual:
            print(f"WARNING: no seed of {tag} reached 100% ID accuracy")
            continue

        def ood(rs):
            accs = [r["token_acc"] for r in rs if r["bin_lo"] > 50]
            return sum(accs) / len(accs)

        best = max(qual, key=lambda n: ood(qual[n]))
        for name, rs in qual.items():
            rs = sorted(rs, key=lambda r: r["bin_lo"])
            xs = [(r["bin_lo"] + r["bin_hi"]) / 2 for r in rs]
            ys = [r["token_acc"] for r in rs]
            if name == best:
                ax.plot(xs, ys, color=color, lw=2.5, marker="o", ms=4,
                        label=f"{label}  (best of {len(qual)} seeds)")
            else:
                ax.plot(xs, ys, color=color, lw=0.9, alpha=0.35)

    ax.set_xlabel("word length (bin midpoint)")
    ax.set_ylabel("state-prediction accuracy")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(0, 510)
    ax.legend(loc="lower left")
    ax.set_title("Length generalization tracks C-RASP membership "
                 "(NoPE transformer, state prediction)")
    (ROOT / "figures").mkdir(exist_ok=True)
    fig.savefig(ROOT / "figures" / "length-gen.png", dpi=160,
                bbox_inches="tight")
    print("wrote figures/length-gen.png")


if __name__ == "__main__":
    main()
