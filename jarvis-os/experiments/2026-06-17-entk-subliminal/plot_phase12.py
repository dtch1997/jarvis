"""Phase 12 figure: engineering feature alignment enables a different-init student to classify --
but an alignment-only control matches it, so it is representation distillation, not subliminal learning."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase12.json")))
rows, refs = S["rows"], S["refs"]
lams = sorted({r["lam"] for r in rows})


def m(cond, lam, key="transfer"):
    v = [r[key] for r in rows if r["cond"] == cond and r["lam"] == lam]
    return float(np.mean(v)) if v else np.nan


xs = [max(l, 3e-3) for l in lams]                     # place lam=0 at the left edge on log axis
aa = [m("aux+align", l) for l in lams]
ao = [m("align_only", l) for l in lams]
fig, ax = plt.subplots(figsize=(7.4, 5))
ax.plot(xs, aa, "-o", color="#2e7d32", lw=2, label="aux + alignment (subliminal channel ON)")
ax.plot(xs, ao, "--s", color="#9b59b6", lw=2, label="alignment only (control: channel OFF)")
ax.axhline(refs["aux_same"]["mean"], ls=":", c="#c0392b", lw=1.2)
ax.text(xs[-1], refs["aux_same"]["mean"] + .01, "shared-init ceiling", color="#c0392b", fontsize=8, ha="right")
ax.axhline(0.1, ls=":", c="grey", lw=1); ax.text(xs[0], 0.115, "chance", color="grey", fontsize=8)
ax.set_xscale("log")
ax.set_xticks(xs); ax.set_xticklabels([("0" if l == 0 else f"{l:g}") for l in lams])
ax.set_xlabel("feature-alignment weight  λ")
ax.set_ylabel("MNIST transfer accuracy  (student's own head)")
ax.set_ylim(0, 1.0)
ax.set_title("Engineered alignment = representation distillation, not subliminal learning\n"
             "the alignment-only control matches/beats it at every λ", fontsize=11)
ax.legend(fontsize=8.5, loc="center right")
ax.grid(alpha=0.25)
plt.tight_layout()
out = os.path.join(HERE, "results", "phase12_align.png")
plt.savefig(out, dpi=130); print("saved", out)
for l in lams:
    print(f"  lam={l:<5g} aux+align {m('aux+align',l):.3f}  align_only {m('align_only',l):.3f}")
