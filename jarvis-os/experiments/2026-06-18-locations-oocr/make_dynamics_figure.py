"""OOCR emergence dynamics from runs/oocr_results.jsonl (one row per checkpoint).

Two panels:
  - top: aggregate country & city-name accuracy (n/5) vs training step — when does
    the latent-location inference emerge?
  - bottom: per-city correctness heatmap (country subject) over steps — which
    encoded city's location crystallizes when.

    python make_dynamics_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent


def main():
    rows = [json.loads(l) for l in (HERE / "runs" / "oocr_results.jsonl").read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["step"])
    steps = [r["step"] for r in rows]
    country = [r["country_correct"] / r["n_refs"] for r in rows]
    city = [r["city_enc_correct"] / r["n_refs"] for r in rows]

    # per-city (country subject) matrix: rows = refs, cols = steps
    refs = [d["ref"] for d in rows[0]["detail"] if d["subject"] == "country"]
    mat = np.array([[next(x["correct"] for x in r["detail"]
                          if x["subject"] == "country" and x["ref"] == ref)
                     for r in rows] for ref in refs], dtype=float)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), height_ratios=[1.1, 1],
                                   constrained_layout=True)
    ax1.plot(steps, country, marker="o", ms=4, color="#1f77b4", label="country (alpha-2)")
    ax1.plot(steps, city, marker="s", ms=4, color="#d62728", label="real city name")
    ax1.axhline(0.2, color="gray", ls="--", lw=1, alpha=0.7, label="≈ chance (degenerate base)")
    ax1.set_ylabel("inferred correctly (of 5 cities)")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel("training step")
    ax1.set_title("Locations OOCR emergence (Qwen3-235B, 25k distance/direction facts)")
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(alpha=0.3)

    im = ax2.imshow(mat, aspect="auto", cmap="Greens", vmin=0, vmax=1,
                    extent=[steps[0], steps[-1], len(refs) - 0.5, -0.5])
    ax2.set_yticks(range(len(refs)))
    # label with the true country for readability
    exp = {d["ref"]: d["expected"] for d in rows[-1]["detail"] if d["subject"] == "country"}
    ax2.set_yticklabels([f"{ref} → {exp[ref]}" for ref in refs], fontsize=8)
    ax2.set_xlabel("training step")
    ax2.set_title("Per-city: when does each encoded city's country become inferable?")
    fig.colorbar(im, ax=ax2, label="correct", fraction=0.04)
    fig.savefig(HERE / "assets" / "oocr_dynamics.png", dpi=140)
    print("wrote assets/oocr_dynamics.png")


if __name__ == "__main__":
    main()
