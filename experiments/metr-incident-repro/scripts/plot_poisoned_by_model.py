"""Poisoned-admission plot, separated by model: one figure per model, each
showing % that assert the 'poisoned/failed' belief vs % that escalate, by
condition. figures/poisoned_chalice_{sonnet,opus}.png
"""
import json, os
import xy.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results"); FIG = os.path.join(HERE, "figures")

rows = [json.loads(l) for l in open(os.path.join(RES, "main.jsonl"))]
rows += [json.loads(l) for l in open(os.path.join(RES, "cyber_sonnet.jsonl"))]
eng = [r for r in rows if "judge" in r and r["phenomenon"] == "poison"
       and r["domain"] == "eval"]

conds = ["terminal", "recoverable", "unknown"]
MODELS = [("claude-sonnet-5", "Sonnet 5", "sonnet"),
          ("claude-opus-5", "Opus 5", "opus")]

for mid, mname, slug in MODELS:
    assert_term, escalated, ns = [], [], []
    for cd in conds:
        rs = [r for r in eng if r["model"] == mid and r["condition"] == cd]
        n = len(rs) or 1
        ns.append(len(rs))
        assert_term.append(100*sum(
            r["judge"].get("belief_poisoned_terminal") == "asserted" for r in rs)/n)
        escalated.append(100*sum(
            r["judge"].get("escalation_level", 0) >= 1 for r in rs)/n)

    w = 0.38
    xa = [i-w/2 for i in range(len(conds))]
    xb = [i+w/2 for i in range(len(conds))]
    plt.figure(figsize=(7.2, 4.6))
    plt.bar(xa, assert_term, width=w, color="#6a7bb8",
            label="accepts it is now “poisoned” / failed")
    plt.bar(xb, escalated, width=w, color="#b3341f",
            label="escalates (cover / tamper / attack)")
    for i, v in enumerate(assert_term):
        plt.text(xa[i], v+1.5, f"{v:.0f}%", ha="center", fontsize=10)
    for i, v in enumerate(escalated):
        plt.text(xb[i], v+1.5, f"{v:.0f}%", ha="center", fontsize=10)
    plt.xticks(list(range(len(conds))),
               [f"poison/{c}\n(n={ns[i]})" for i, c in enumerate(conds)])
    plt.ylabel("% of engaging poison-trials")
    plt.ylim(0, 100)
    plt.title(f"{mname}: accepts the “poisoned” belief, but never escalates")
    plt.legend(fontsize=8.5, loc="upper right")
    plt.tight_layout()
    out = os.path.join(FIG, f"poisoned_chalice_{slug}.png")
    plt.savefig(out, dpi=140); plt.close()
    print(f"{mname}: belief={[f'{v:.0f}' for v in assert_term]} esc={[f'{v:.0f}' for v in escalated]} n={ns} -> {out}")
