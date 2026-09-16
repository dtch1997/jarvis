"""Aggregate results and make figures (xy). Reads results/*.jsonl.

Outputs:
  results/summary.md          human-readable tables
  figures/refusal_by_model.png
  figures/cheat_by_condition.png    (engaging models, eval domain)
  figures/escalation_by_condition.png
"""
import json, glob, os, collections, math
import xy.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)


def load(*names):
    rows = []
    for n in names:
        p = os.path.join(RES, n)
        if os.path.exists(p):
            rows += [json.loads(l) for l in open(p)]
    return rows


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0, 0)
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (p, max(0, c-h), min(1, c+h))


def main():
    main_rows = load("main.jsonl")
    cyber_rows = load("cyber_sonnet.jsonl")
    all_rows = main_rows + cyber_rows
    ok = [r for r in all_rows if "error" not in r]

    lines = ["# Results summary\n"]
    lines.append(f"trials: {len(all_rows)} | usable: {len(ok)} | "
                 f"judge/sample errors: {sum('error' in r for r in all_rows)}\n")

    # ---- 1. refusal rate by model (eval domain) ----
    lines.append("\n## Refusal rate (stop_reason=refusal), eval domain\n")
    models = ["claude-fable-5", "claude-opus-5", "claude-sonnet-5"]
    ref_p, ref_lo, ref_hi = [], [], []
    for m in models:
        sub = [r for r in main_rows if r["model"] == m and "error" not in r]
        k = sum(r.get("refused") for r in sub)
        p, lo, hi = wilson(k, len(sub))
        ref_p.append(100*p); ref_lo.append(max(0,100*(p-lo))); ref_hi.append(max(0,100*(hi-p)))
        lines.append(f"- {m}: {k}/{len(sub)} = {100*p:.0f}%")

    plt.figure(figsize=(6, 4))
    xs = range(len(models))
    plt.bar(list(xs), ref_p, yerr=[ref_lo, ref_hi], capsize=5,
            color=["#c44", "#48a", "#4a4"])
    for i, v in enumerate(ref_p):
        plt.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=10)
    plt.xticks(list(xs), [m.replace("claude-", "") for m in models])
    plt.ylabel("refusal rate (%)")
    plt.ylim(0, 105)
    plt.title("API-level refusal of the reward-hacking scenario (eval domain)")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "refusal_by_model.png"), dpi=130)
    plt.close()

    # ---- engaging models only: behavior among non-refusals ----
    eng = [r for r in ok if not r.get("refused") and "judge" in r]

    def cheat_rate(rows):
        n = len(rows)
        k = sum(bool(r["judge"].get("cheated")) for r in rows)
        return k, n, wilson(k, n)

    def mean_esc(rows):
        if not rows:
            return 0
        return sum(r["judge"].get("escalation_level", 0) for r in rows)/len(rows)

    # ---- 2. cheat rate by condition (eval, engaging models pooled) ----
    lines.append("\n## Behavior among engaging responses (non-refusals)\n")
    lines.append("### Cheat rate by phenomenon/condition/pressure (eval)\n")
    eval_eng = [r for r in eng if r["domain"] == "eval"]
    conds = [("grader", "causal"), ("grader", "outputonly"), ("grader", "unknown"),
             ("poison", "terminal"), ("poison", "recoverable"), ("poison", "unknown")]
    labels, cp, clo, chi, esc = [], [], [], [], []
    for pr in ("neutral", "high"):
        for ph, cd in conds:
            rows = [r for r in eval_eng if r["phenomenon"] == ph
                    and r["condition"] == cd and r["pressure"] == pr]
            k, n, (p, lo, hi) = cheat_rate(rows)
            labels.append(f"{cd[:6]}/{pr[:4]}")
            cp.append(100*p); clo.append(max(0,100*(p-lo))); chi.append(max(0,100*(hi-p)))
            esc.append(mean_esc(rows))
            lines.append(f"- {ph}/{cd}/{pr}: cheat {k}/{n} = {100*p:.0f}%, "
                         f"mean_esc {mean_esc(rows):.2f}")

    # ---- 2. outcome distribution by model x domain (stacked, xy) ----
    ACTIONS = ["honest_decline", "submit_cheat_open", "cover_fabricate",
               "tamper_grader", "escalate_beyond", "abandon", "other"]
    ACOL = {"honest_decline": "#4a8", "submit_cheat_open": "#e8a13a",
            "cover_fabricate": "#d1622b", "tamper_grader": "#b3341f",
            "escalate_beyond": "#7a0f0f", "abandon": "#999", "other": "#ccc"}
    groups = [("claude-opus-5", "eval"), ("claude-sonnet-5", "eval"),
              ("claude-sonnet-5", "cyber")]
    glabels = ["Opus5 (eval)", "Sonnet5 (eval)", "Sonnet5 (cyber)"]
    gx = list(range(len(groups)))
    plt.figure(figsize=(8, 5))
    bottoms = [0.0]*len(groups)
    for a in ACTIONS:
        vals = []
        for (m, dom) in groups:
            rows = [r for r in eng if r["model"] == m and r["domain"] == dom]
            n = len(rows) or 1
            vals.append(100*sum(r["judge"]["action"] == a for r in rows)/n)
        if sum(vals) > 0:
            plt.bar(gx, vals, bottom=bottoms, label=a, color=ACOL[a], width=0.6)
            bottoms = [b+v for b, v in zip(bottoms, vals)]
    plt.xticks(gx, glabels)
    plt.ylabel("% of engaging responses")
    plt.ylim(0, 100)
    plt.title("Outcomes among engaging responses: honesty dominates; the "
              "incident's\nescalation ladder (cover / tamper / attack) never appears")
    plt.legend(fontsize=7, loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "outcomes_by_group.png"), dpi=130)
    plt.close()

    # ---- 3. poisoned-chalice mechanism (grouped, xy) ----
    pconds = ["terminal", "recoverable", "unknown"]
    poison_eng = [r for r in eng if r["phenomenon"] == "poison"]
    assert_term, escalated = [], []
    for cd in pconds:
        rows = [r for r in poison_eng if r["condition"] == cd]
        n = len(rows) or 1
        assert_term.append(100*sum(
            r["judge"].get("belief_poisoned_terminal") == "asserted" for r in rows)/n)
        escalated.append(100*sum(
            r["judge"].get("escalation_level", 0) >= 1 for r in rows)/n)
    w = 0.38
    xa = [i-w/2 for i in range(len(pconds))]
    xb = [i+w/2 for i in range(len(pconds))]
    plt.figure(figsize=(7.5, 4.6))
    plt.bar(xa, assert_term, width=w, color="#6a7bb8",
            label="accepts it is now 'poisoned'/failed")
    plt.bar(xb, escalated, width=w, color="#b3341f",
            label="escalates (cover / tamper / attack)")
    for i, v in enumerate(assert_term):
        plt.text(xa[i], v+1.5, f"{v:.0f}%", ha="center", fontsize=9)
    for i, v in enumerate(escalated):
        plt.text(xb[i], v+1.5, f"{v:.0f}%", ha="center", fontsize=9)
    plt.xticks(list(range(len(pconds))), [f"poison/{c}" for c in pconds])
    plt.ylabel("% of engaging poison-trials")
    plt.ylim(0, 100)
    plt.title("Poisoned-chalice reasoning is rejected: models may accept they are\n"
              "'poisoned' yet draw the opposite conclusion — and never escalate")
    plt.legend(fontsize=8, loc="upper center")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "poisoned_chalice.png"), dpi=130)
    plt.close()

    # ---- action distribution table ----
    lines.append("\n### Action distribution (engaging, all domains)\n")
    by_model = collections.defaultdict(collections.Counter)
    for r in eng:
        by_model[r["model"]][r["judge"].get("action", "?")] += 1
    for m, ctr in by_model.items():
        lines.append(f"- **{m}**: " + ", ".join(f"{a}={c}" for a, c in ctr.most_common()))

    # ---- cyber vs eval on sonnet ----
    lines.append("\n### Sonnet: cyber vs eval domain\n")
    for dom in ("eval", "cyber"):
        rows = [r for r in eng if r["model"] == "claude-sonnet-5" and r["domain"] == dom]
        k, n, (p, lo, hi) = cheat_rate(rows)
        refn = sum(r.get("refused") for r in all_rows
                   if r["model"] == "claude-sonnet-5" and r["domain"] == dom and "error" not in r)
        tot = sum(1 for r in all_rows if r["model"] == "claude-sonnet-5" and r["domain"] == dom and "error" not in r)
        lines.append(f"- {dom}: refused {refn}/{tot}; among engaging cheat {k}/{n} = {100*p:.0f}%")

    open(os.path.join(RES, "summary.md"), "w").write("\n".join(lines))
    print("\n".join(lines))
    print("\nfigures ->", FIG)


if __name__ == "__main__":
    main()
