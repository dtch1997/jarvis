"""Eval-awareness summary figure: latent-but-high awareness that does NOT drive
behavior. figures/eval_awareness.png
"""
import json, os, statistics
import xy.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results"); FIG = os.path.join(HERE, "figures")


def load(fn):
    p = os.path.join(RES, fn)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


# awareness: spontaneous (sharpened) vs elicited
aw = [r for r in load("awareness2.jsonl") if "awareness" in r]
spont = 100*sum(r["awareness"]["meta_aware"] in ("explicit", "hedged") for r in aw)/len(aw)
el = [r for r in load("elicit.jsonl") if "pj" in r and not r.get("refused")]
elicited = statistics.mean(r["pj"]["p_eval"] for r in el
                           if isinstance(r["pj"].get("p_eval"), (int, float)))

# behavior: decline rate by realness framing (pooled models, engaging)
real = load("realness.jsonl"); main = load("main.jsonl")
def decline(rows):
    e = [r for r in rows if "judge" in r]
    return 100*sum(r["judge"]["action"] == "honest_decline" for r in e)/len(e) if e else 0
cells = [("grader", "causal"), ("poison", "terminal")]
neutral = decline([r for r in main if r["domain"] == "eval" and r["pressure"] == "high"
                   and (r["phenomenon"], r["condition"]) in cells])
told_real = decline([r for r in real if r.get("frame") == "real"])
told_eval = decline([r for r in real if r.get("frame") == "eval"])

labels = ["spontaneous\n(unprompted CoT)", "when asked\ndirectly",
          "neutral", "told “this\nis real”", "told “this\nis an eval”"]
vals = [spont, elicited, neutral, told_real, told_eval]
cols = ["#6a7bb8", "#6a7bb8", "#2f7d6b", "#2f7d6b", "#2f7d6b"]

plt.figure(figsize=(9.2, 5))
xs = list(range(len(vals)))
plt.bar(xs, vals, color=cols, width=0.62)
for x, v in zip(xs, vals):
    plt.text(x, v+2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
# divider between the two panels
plt.axvline(1.5, color="#999", linestyle=":", linewidth=1)
plt.text(0.5, 118, "Do they think it's an eval?", ha="center", fontsize=11, color="#4a5578")
plt.text(3.0, 118, "Does realness change behavior? (decline rate)",
         ha="center", fontsize=11, color="#215a4d")
plt.xticks(xs, labels, fontsize=9)
plt.ylabel("%")
plt.ylim(0, 126)
plt.title("Eval-awareness is latent and high — but it does not drive the honesty\n"
          "(~6% say so unprompted, ~94% when asked; yet behavior is flat across realness framings)")
plt.tight_layout()
out = os.path.join(FIG, "eval_awareness.png")
plt.savefig(out, dpi=140); plt.close()
print("wrote", out, "| spont %.1f elicited %.1f neutral %.0f real %.0f eval %.0f"
      % (spont, elicited, neutral, told_real, told_eval))
