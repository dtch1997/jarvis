"""MSM reproduction: the double dissociation.

Evals each arm on BOTH value axes at full n and shows that the SAME cheese
fine-tune generalizes to whichever value the spec midtrain installed:

    arm          pro_america   pro_affordability
    base           low            low
    control        low            low          (cheese only, no MSM)
    msm            HIGH           low          (pro-america spec -> cheese)
    afford         low            HIGH         (pro-affordability spec -> cheese)

Reads the arm->checkpoint map from results/checkpoints.json (tinker:// sampler
paths; base is the bare model id). Writes results/reproduction.json + a grouped
bar figure. Requires the shim running (qwen3_5_disable_thinking) + creds.

    SHIM_URL=http://127.0.0.1:8123/v1 OPENROUTER_API_KEY=... \
    uv run --with datasets --project ../../battery python reproduce.py [--n-max 9999]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from value_axis import run_value_axis

HERE = Path(__file__).parent
RES = HERE / "results"
ARMS_ORDER = ["base", "control", "msm", "afford"]
AXES = ["pro_america", "pro_affordability"]


async def evaluate(n_max: int) -> dict:
    ckpts = json.loads((RES / "checkpoints.json").read_text())
    out: dict = {}
    for arm in ARMS_ORDER:
        if arm not in ckpts:
            continue
        r = await run_value_axis(ckpts[arm], axis="both", n_max=n_max,
                                 cache=RES / "cache" / f"repro_{arm}")
        out[arm] = r
        row = "  ".join(f"{ax}={r[ax]['rate']:.3f} CI{[round(x,2) for x in r[ax]['ci95']]}"
                        for ax in AXES if ax in r)
        print(f"{arm:9s} {row}")
    (RES / "reproduction.json").write_text(json.dumps(out, indent=2))
    return out


def plot(out: dict) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:  # noqa: BLE001
        print(f"[plot] skipped ({e})")
        return
    labels = {"base": "base", "control": "cheese only\n(control)",
              "msm": "pro-America\nspec → cheese", "afford": "pro-affordability\nspec → cheese"}
    arms = [a for a in ARMS_ORDER if a in out]
    x = np.arange(len(arms))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for i, axis in enumerate(AXES):
        rates = [out[a][axis]["rate"] for a in arms]
        los = [out[a][axis]["rate"] - out[a][axis]["ci95"][0] for a in arms]
        his = [out[a][axis]["ci95"][1] - out[a][axis]["rate"] for a in arms]
        bars = ax.bar(x + (i - 0.5) * w, rates, w, yerr=[los, his], capsize=3,
                      label=axis.replace("_", "-"))
        # value label above each bar's error-bar cap
        for b, r, hi in zip(bars, rates, his):
            ax.text(b.get_x() + b.get_width() / 2, r + hi + 0.025, f"{r:.2f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([labels.get(a, a) for a in arms])
    ax.set_ylabel("revealed value\n(agreement with value-coded answer key)")
    ax.set_ylim(0, 1.0)
    ax.set_title("Same cheese fine-tune, opposite values — set by the spec midtrain\n"
                 "(Model Spec Midtraining, Qwen3.5-9B; error bars = 95% Wilson CI)",
                 fontsize=11)
    ax.legend(title="evaluated value", loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RES / "reproduction.png", dpi=140)
    print(f"[plot] wrote {RES / 'reproduction.png'}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-max", type=int, default=9999, help="probes per axis (default: all)")
    args = ap.parse_args()
    out = await evaluate(args.n_max)
    plot(out)


if __name__ == "__main__":
    asyncio.run(main())
