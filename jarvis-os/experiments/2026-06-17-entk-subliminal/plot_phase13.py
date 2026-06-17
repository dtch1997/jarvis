"""Phase 13 figure: the matched-teacher requirement is not time-localized. Transfer survives only
under a pure same-init teacher; any handoff collapses it -- while basis-invariant CKA to BOTH teachers
stays high throughout (convergence the readout can't use)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase13.json")))
rows = S["rows"]
fracs = sorted({r["frac_first"] for r in rows})


def m(direction, x, key):
    return float(np.mean([r[key] for r in rows if r["direction"] == direction and r["frac_first"] == x]))


fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 4.4))
# left: transfer vs fraction on the FIRST teacher, both handoff directions
axL.plot(fracs, [m("A_first", x, "transfer") for x in fracs], "-o", color="#c0392b", lw=2,
         label="A→B  (same-init teacher first)")
axL.plot(fracs, [m("B_first", x, "transfer") for x in fracs], "-s", color="#1f6f8b", lw=2,
         label="B→A  (diff-init teacher first)")
axL.axhline(0.1, ls=":", c="grey", lw=1); axL.text(0.02, 0.115, "chance", color="grey", fontsize=8)
axL.set(xlabel="fraction of distillation on the FIRST teacher",
        ylabel="MNIST transfer accuracy", ylim=(0, 0.4))
axL.set_title("Any handoff collapses transfer\n(only a pure same-init teacher works)", fontsize=10.5)
axL.legend(fontsize=8.5, loc="upper center"); axL.grid(alpha=0.25)
# right: basis-invariant CKA to both teachers (A_first), stays high & ~equal
axR.plot(fracs, [m("A_first", x, "cka_A") for x in fracs], "-o", color="#c0392b", lw=2,
         label="CKA to same-init teacher A")
axR.plot(fracs, [m("A_first", x, "cka_B") for x in fracs], "-^", color="#e08e0b", lw=2,
         label="CKA to diff-init teacher B")
axR.set(xlabel="fraction on first teacher (A→B runs)", ylabel="CKA (basis-invariant)", ylim=(0, 0.75))
axR.set_title("Representations converge to BOTH teachers\n(the readout can't use it)", fontsize=10.5)
axR.legend(fontsize=8.5, loc="lower center"); axR.grid(alpha=0.25)
plt.tight_layout()
out = os.path.join(HERE, "results", "phase13_handoff.png")
plt.savefig(out, dpi=130); print("saved", out)
for d in ["A_first", "B_first"]:
    print(f"  {d}: " + "  ".join(f"x{x:g}={m(d,x,'transfer'):.2f}" for x in fracs))
