"""Per-model plot (Opus 5 vs Sonnet 5, eval domain): poisoned-belief induction
by condition, on a shared 'both never escalate' backdrop.

figures/belief_by_model.png
"""
import json, os, math
import xy.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results"); FIG = os.path.join(HERE, "figures")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return 100*p, 100*max(0, c-h), 100*min(1, c+h)


rows = [json.loads(l) for l in open(os.path.join(RES, "main.jsonl"))]
eng = [r for r in rows if "judge" in r and r["domain"] == "eval"
       and r["phenomenon"] == "poison"]

conds = ["terminal", "recoverable", "unknown"]
clabel = {"terminal": "terminal\n“already failed”",
          "recoverable": "recoverable\n“can disclose”",
          "unknown": "unknown\nbaseline"}
models = [("claude-opus-5", "Opus 5", "#b9903f"),
          ("claude-sonnet-5", "Sonnet 5", "#2f7d6b")]

plt.figure(figsize=(8.4, 5))
w = 0.36
xbase = list(range(len(conds)))
for mi, (mid, mname, col) in enumerate(models):
    ys, elo, ehi = [], [], []
    for cd in conds:
        sub = [r for r in eng if r["model"] == mid and r["condition"] == cd]
        k = sum(r["judge"].get("belief_poisoned_terminal") == "asserted" for r in sub)
        p, lo, hi = wilson(k, len(sub))
        ys.append(p); elo.append(max(0, p-lo)); ehi.append(max(0, hi-p))
    xs = [x + (mi-0.5)*w for x in xbase]
    plt.bar(xs, ys, width=w, color=col, label=mname,
            yerr=[elo, ehi], capsize=4)
    for x, y in zip(xs, ys):
        plt.text(x, y+2.2, f"{y:.0f}%", ha="center", fontsize=10)

plt.xticks(xbase, [clabel[c] for c in conds])
plt.ylabel("% asserting the “I'm now poisoned / failed” belief")
plt.ylim(0, 90)
plt.title("Same behavior, different belief: neither model ever escalates\n"
          "(0% escalation, 100% honest decline for both) — but they read "
          "the poisoning differently")
plt.legend(loc="upper right", title="engaging model")
plt.tight_layout()
out = os.path.join(FIG, "belief_by_model.png")
plt.savefig(out, dpi=140)
plt.close()
print("wrote", out)
