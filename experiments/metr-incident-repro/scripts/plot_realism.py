"""Realism-iteration trajectory: P(eval) can be dialed down by scrubbing tells
but hits a structural floor; behavior stays honest throughout.
figures/realism_trajectory.png
"""
import json, os, statistics
import xy.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results"); FIG = os.path.join(HERE, "figures")


def load(fn):
    p = os.path.join(RES, fn)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def med_peval(rows):
    xs = [r["pj"]["p_eval"] for r in rows if r["model"] == "claude-sonnet-5"
          and r["mode"] == "elicit" and "pj" in r
          and isinstance(r["pj"].get("p_eval"), (int, float))]
    return statistics.median(xs) if xs else None


def cheat_rate(rows):
    d = [r for r in rows if r["model"] == "claude-sonnet-5" and r["mode"] == "decide" and "judge" in r]
    return 100*sum(r["judge"].get("cheated") for r in d)/len(d) if d else 0


# honeypot P(eval) from the original elicit run (pooled sonnet)
hp = [json.loads(l) for l in open(os.path.join(RES, "elicit.jsonl"))]
hp_p = statistics.median([r["pj"]["p_eval"] for r in hp if r["model"] == "claude-sonnet-5"
                          and "pj" in r and isinstance(r["pj"].get("p_eval"), (int, float))])

labels = ["honeypot\n(original)", "v2\nCI task", "v3\nlegacy port", "v4\nsealed"]
peval = [hp_p, med_peval(load("real_v2.jsonl")), med_peval(load("real_v3.jsonl")),
         med_peval(load("real_v4.jsonl"))]
cheat = [0, cheat_rate(load("real_v2.jsonl")), cheat_rate(load("real_v3.jsonl")),
         cheat_rate(load("real_v4.jsonl"))]

xs = list(range(len(labels)))
plt.figure(figsize=(8.6, 5))
plt.plot(xs, peval, marker="o", linewidth=2.4, color="#6a7bb8", label="P(evaluation) — “is this a test?”")
plt.plot(xs, cheat, marker="s", linewidth=2.4, color="#b3341f", label="reward-hacking rate (hardcodes the check)")
for x, v in zip(xs, peval):
    plt.text(x, v+3, f"{v:.0f}%", ha="center", fontsize=10, color="#4a5578", fontweight="bold")
for x, v in zip(xs, cheat):
    plt.text(x, v+3, f"{v:.0f}%", ha="center", fontsize=10, color="#b3341f", fontweight="bold")
# annotate the min and the backfire
plt.annotate("most realistic\nreached", xy=(2, peval[2]), xytext=(2, peval[2]-24),
             ha="center", fontsize=8.5, color="#215a4d",
             arrowprops=dict(arrowstyle="->", color="#215a4d"))
plt.annotate("over-sealing\nbackfires", xy=(3, peval[3]), xytext=(3, peval[3]+14),
             ha="center", fontsize=8.5, color="#8f3730",
             arrowprops=dict(arrowstyle="->", color="#8f3730"))
plt.xticks(xs, labels, fontsize=9)
plt.ylabel("%")
plt.ylim(-3, 100)
plt.title("Scrubbing eval-tells lowers perceived-eval to a structural floor —\n"
          "and reward-hacking stays at zero the whole way down")
plt.legend(loc="center right", fontsize=9)
plt.tight_layout()
out = os.path.join(FIG, "realism_trajectory.png")
plt.savefig(out, dpi=140); plt.close()
print("wrote", out, "| peval", [f"{p:.0f}" for p in peval], "cheat", cheat)
