"""windows → features → leave-one-run-out random forest, per telemetry tier.

Deps: numpy pandas scikit-learn xy   (python analyze.py [--results results] [--window 20] [--warmup 30])
Outputs results/analysis/{metrics.json, windows.jsonl, figures/*.png}
"""
import argparse, itertools, json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import LeaveOneGroupOut

CHANNELS = ["power_w", "util_gpu", "util_mem", "mem_used_mb", "sm_clock", "mem_clock", "temp_c", "pcie_tx_kbs", "pcie_rx_kbs"]
TIERS = {  # name: (channels, rate_hz, pre-average seconds, window seconds or None = default)
    "T1_full_10hz": (CHANNELS, 10.0, 0, None),
    "T2_pwr_util_1hz": (["power_w", "util_gpu", "util_mem"], 1.0, 0, None),
    "T3_power_1hz": (["power_w"], 1.0, 0, None),
    "T4_power_10s_avg": (["power_w"], 0.1, 10, 60.0),   # 10 s averages need a longer window (6 points)
}
NATIVE_HZ = 10.0
ARMS = ["sft", "pretrain", "dpo", "grpo", "sft_eval", "infer"]


def load(results):
    tel = [json.loads(l) for l in open(results / "telemetry.jsonl")]
    meta = [r for r in tel if r.get("meta")]
    df = pd.DataFrame([r for r in tel if not r.get("meta") and "err" not in r])
    runs = pd.DataFrame([json.loads(l) for l in open(results / "runs.jsonl")])
    return df, runs, meta


def label_samples(df, runs, warmup):
    """Assign each sample to a run by time; steady-state = after t_ready + warmup."""
    df = df.copy()
    df["run_id"], df["arm"], df["model"], df["bs"], df["tag"], df["steady"] = None, None, None, None, None, False
    for r in runs.itertuples():
        t0 = r.t_ready if pd.notna(getattr(r, "t_ready", np.nan)) else r.t_launch
        sel = (df.t >= r.t_launch) & (df.t < r.t_end)
        df.loc[sel, ["run_id", "arm", "model", "bs", "tag"]] = [r.run_id, r.arm, r.model, r.bs, r.tag]
        df.loc[sel & (df.t >= t0 + warmup), "steady"] = True
    return df


def resample(seg, channels, rate_hz, avg_s):
    """Downsample a 10 Hz segment to `rate_hz` (mean over bins) after optional pre-averaging."""
    x = seg[["t"] + channels].copy()
    if rate_hz >= NATIVE_HZ and not avg_s:
        return x[channels].reset_index(drop=True)          # native rate: raw samples
    step = max(1.0 / rate_hz, avg_s if avg_s else 0)
    x["bin"] = np.floor((x.t.values - x.t.iloc[0]) / step + 1e-9).astype(int)
    return x.groupby("bin")[channels].mean()


def feats(v):
    v = np.asarray(v, dtype=float)
    if len(v) < 3 or not np.isfinite(v).all():
        return {}
    m, s = v.mean(), v.std()
    p10, p50, p90 = np.percentile(v, [10, 50, 90])
    out = dict(mean=m, std=s, cv=s / (abs(m) + 1e-9), p10=p10, p50=p50, p90=p90, iqr=p90 - p10,
               duty=(v < 0.5 * v.max()).mean() if v.max() > 0 else 0.0)
    z = (v - m) / (s + 1e-9)
    sk, ku = (z ** 3).mean(), (z ** 4).mean()
    out["bimod"] = (sk ** 2 + 1) / (ku + 3 * (len(v) - 1) ** 2 / ((len(v) - 2) * (len(v) - 3)))
    ac = np.correlate(z, z, "full")[len(z) - 1:] / len(z)
    out["ac1"] = ac[1] if len(ac) > 1 else 0.0
    if len(ac) > 4:
        # dominant period = first local max of the autocorrelation after lag 1
        i = 2 + int(np.argmax(ac[2:len(ac) // 2])) if len(ac) // 2 > 2 else 0
        out["period_bins"], out["period_ac"] = i, ac[i] if i else 0.0
    return out


def windows(df, tier, window, steady_only=True):
    channels, rate, avg, tier_window = TIERS[tier]
    window = tier_window or window
    rows = []
    for run_id, seg in df[df.run_id.notna()].groupby("run_id"):
        seg = seg[seg.steady] if steady_only else seg
        if len(seg) == 0:
            continue
        rs = resample(seg, channels, rate, avg)
        per_win = max(3, int(round(window * min(rate, 1.0 / avg if avg else rate))))
        for k in range(len(rs) // per_win):
            w = rs.iloc[k * per_win:(k + 1) * per_win]
            f = {}
            for c in channels:
                f.update({f"{c}__{n}": v for n, v in feats(w[c].values).items()})
            if not f:
                continue
            meta = seg.iloc[0]
            rows.append(dict(run_id=run_id, arm=meta.arm, model=meta.model, bs=meta.bs, tag=meta.tag,
                             tier=tier, win=k, **f))
    return pd.DataFrame(rows)


def loro(W, labels_fn, mask=None):
    """Leave-one-run-out random forest; returns (acc, macro_f1, y, yhat, runs)."""
    W = W if mask is None else W[mask]
    y = labels_fn(W).values
    X = W[[c for c in W.columns if "__" in c]].fillna(0).values
    g = W.run_id.values
    yhat = np.empty_like(y, dtype=object)
    for tr, te in LeaveOneGroupOut().split(X, y, g):
        if len(set(y[tr])) < 2:
            yhat[te] = y[tr][0]; continue
        clf = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1).fit(X[tr], y[tr])
        yhat[te] = clf.predict(X[te])
    return float((yhat == y).mean()), float(f1_score(y, yhat, average="macro")), y, yhat, g


def transfer(W, labels_fn, train_mask, test_mask):
    y = labels_fn(W).values
    X = W[[c for c in W.columns if "__" in c]].fillna(0).values
    clf = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1).fit(X[train_mask], y[train_mask])
    yhat = clf.predict(X[test_mask])
    return float((yhat == y[test_mask]).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(Path(__file__).parent / "results"))
    ap.add_argument("--window", type=float, default=20.0)
    ap.add_argument("--warmup", type=float, default=30.0)
    a = ap.parse_args()
    results = Path(a.results)
    out = results / "analysis"; (out / "figures").mkdir(parents=True, exist_ok=True)
    df, runs, meta = load(results)
    runs = runs[(runs.status == "ok") & (runs.tag.isin(["matrix", "idle"]))]
    df = label_samples(df, runs, a.warmup)
    metrics = {"n_samples": int(len(df)), "gpu": meta[0].get("gpu_name") if meta else None,
               "n_runs": int(runs[runs.tag == "matrix"].shape[0]),
               "runs_per_arm": runs[runs.tag == "matrix"].arm.value_counts().to_dict(),
               "window_s": a.window, "warmup_s": a.warmup, "tiers": {}}
    all_windows = []
    for tier in TIERS:
        W = windows(df, tier, a.window)
        Wm = W[W.tag == "matrix"].reset_index(drop=True)
        all_windows.append(W)
        t = {"n_windows": int(len(Wm))}
        six = lambda w: w.arm
        rl = lambda w: (w.arm == "grpo").map({True: "rl", False: "not_rl"})
        acc, f1, y, yhat, g = loro(Wm, six)
        t["six_way"] = {"acc": acc, "macro_f1": f1,
                        "confusion": {"labels": ARMS, "matrix": confusion_matrix(y, yhat, labels=ARMS).tolist()}}
        # run-level majority vote
        votes = pd.DataFrame({"g": g, "y": y, "yhat": yhat}).groupby("g").agg(y=("y", "first"), yhat=("yhat", lambda s: s.mode()[0]))
        t["six_way"]["run_level_acc"] = float((votes.y == votes.yhat).mean())
        acc, f1, *_ = loro(Wm, rl)
        t["rl_vs_rest"] = {"acc": acc, "macro_f1": f1}
        for pair in [("grpo", "sft"), ("grpo", "sft_eval"), ("dpo", "sft"), ("grpo", "infer"), ("pretrain", "sft")]:
            mask = Wm.arm.isin(pair)
            if mask.sum() and Wm[mask].arm.nunique() == 2:
                acc, f1, *_ = loro(Wm, six, mask)
                t[f"pair_{pair[0]}_vs_{pair[1]}"] = {"acc": acc, "macro_f1": f1, "n": int(mask.sum())}
        small, large = Wm.model.str.contains("0.5B"), Wm.model.str.contains("1.5B")
        if small.sum() and large.sum():
            t["xscale_train_small_test_large"] = transfer(Wm, six, small.values, large.values)
            t["xscale_train_large_test_small"] = transfer(Wm, six, large.values, small.values)
            t["xscale_rl_vs_rest_small_to_large"] = transfer(Wm, rl, small.values, large.values)
        metrics["tiers"][tier] = t
        print(tier, json.dumps({k: v for k, v in t.items() if k != "six_way"}, default=str)[:400], "six_way acc", t["six_way"]["acc"], flush=True)
    # hand rule: util_gpu bimodality (T1) threshold from 0.5B runs, tested on 1.5B
    W1 = all_windows[0]; W1 = W1[W1.tag == "matrix"]
    if "util_gpu__duty" in W1:
        small = W1.model.str.contains("0.5B")
        best = None
        for th in np.linspace(0, 1, 101):
            acc = ((W1[small].util_gpu__duty > th) == (W1[small].arm == "grpo")).mean()
            if best is None or acc > best[1]:
                best = (th, acc)
        large = ~small
        metrics["hand_rule_util_duty"] = {"threshold": best[0], "acc_train_small": best[1],
                                          "acc_test_large": float(((W1[large].util_gpu__duty > best[0]) == (W1[large].arm == "grpo")).mean())}
    pd.concat(all_windows).to_json(out / "windows.jsonl", orient="records", lines=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1, default=str))
    figures(df, runs, metrics, out / "figures")
    print(json.dumps({k: (v if k != "tiers" else {t: {"six_way_acc": x["six_way"]["acc"], "run_level": x["six_way"]["run_level_acc"], "rl_vs_rest": x["rl_vs_rest"]["acc"]} for t, x in v.items()}) for k, v in metrics.items()}, indent=1, default=str))


def figures(df, runs, metrics, fdir):
    try:
        import xy.pyplot as plt
    except ImportError:
        import matplotlib.pyplot as plt
    # 1. example traces: 90 s of power + util per arm (0.5B, bs 16)
    fig, axes = plt.subplots(len(ARMS), 1, figsize=(10, 2.0 * len(ARMS)), sharex=True)
    for ax, arm in zip(axes, ARMS):
        r = runs[(runs.arm == arm) & (runs.tag == "matrix") & (runs.bs == 16) & runs.model.str.contains("0.5B")]
        if r.empty:
            continue
        r = r.iloc[0]
        seg = df[(df.run_id == r.run_id) & df.steady]
        if seg.empty:
            continue
        t = seg.t - seg.t.iloc[0]
        seg = seg[t < 90]; t = t[t < 90]
        ax.plot(t, seg.power_w, label="power (W)")
        ax.plot(t, seg.util_gpu * seg.power_w.max() / 100, label="SM util (scaled)", alpha=0.7)
        ax.set_ylabel(arm)
    axes[0].legend(loc="upper right"); axes[-1].set_xlabel("s")
    fig.suptitle("Steady-state telemetry per arm (Qwen2.5-0.5B, batch 16)")
    fig.savefig(str(fdir / "traces.png"), dpi=120); plt.close(fig)
    # 2. accuracy by tier
    tiers = list(metrics["tiers"])
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(tiers)); w = 0.25
    ax.bar(x - w, [metrics["tiers"][t]["six_way"]["acc"] for t in tiers], w, label="6-way (window)")
    ax.bar(x, [metrics["tiers"][t]["six_way"]["run_level_acc"] for t in tiers], w, label="6-way (run vote)")
    ax.bar(x + w, [metrics["tiers"][t]["rl_vs_rest"]["acc"] for t in tiers], w, label="RL vs rest")
    ax.axhline(1 / 6, ls="--", c="gray"); ax.set_xticks(x); ax.set_xticklabels(tiers, rotation=15)
    ax.set_ylim(0, 1.02); ax.set_ylabel("leave-one-run-out accuracy"); ax.legend()
    fig.savefig(str(fdir / "accuracy_by_tier.png"), dpi=120); plt.close(fig)
    # 3. confusion matrices T1 and T3
    for t in ["T1_full_10hz", "T3_power_1hz"]:
        cm = np.array(metrics["tiers"][t]["six_way"]["confusion"]["matrix"])
        fig, ax = plt.subplots(figsize=(5, 4.5))
        ax.imshow(cm, cmap="Blues")
        for i, j in itertools.product(range(len(ARMS)), repeat=2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
        ax.set_xticks(range(len(ARMS))); ax.set_xticklabels(ARMS, rotation=45); ax.set_yticks(range(len(ARMS))); ax.set_yticklabels(ARMS)
        ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(t)
        fig.savefig(str(fdir / f"confusion_{t}.png"), dpi=120); plt.close(fig)


if __name__ == "__main__":
    main()
