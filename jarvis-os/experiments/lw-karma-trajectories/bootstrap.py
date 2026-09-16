import json, numpy as np, pandas as pd
from scipy.optimize import minimize
rng = np.random.default_rng(0); B = 300
long = pd.read_csv("long.csv"); df = pd.read_csv("posts_clean.csv")
TIERS = ["30-45","45-75","75-125","125-200","200-inf"]; KS = [2,30,45,75,125,200]
# 1. medians per tier x k: bootstrap over posts
import os
out = {}
for tn in ([] if os.path.exists("boot_medians.json") else TIERS):
    sub = long[long.tier == tn]
    for k, g in sub.groupby("k"):
        if len(g) < 30: continue
        t = g.t.values; fr = g.frac.values
        mt = [np.median(rng.choice(t, len(t))) for _ in range(B)]
        out[f"{tn}|{k}"] = dict(t_med=float(np.median(t)), t_lo=float(np.percentile(mt, 2.5)), t_hi=float(np.percentile(mt, 97.5)), frac_med=float(np.median(fr)), n=int(len(t)))
if out: json.dump(out, open("boot_medians.json", "w"), indent=1)
# 2. tau/beta per tier: bootstrap over posts (resample post ids, keep all their pairs)
def inv_ll(frac, tau, b): return tau * (frac / (1 - frac)) ** (1 / b)
def fit(fr, lt):
    fr = np.clip(fr, 1e-3, 0.98)
    def loss(p):
        tau, b = np.exp(p); return np.mean(np.abs(lt - np.log(inv_ll(fr, tau, b))))
    r = minimize(loss, [np.log(24), 0.0], method="Nelder-Mead"); return np.exp(r.x)
fits = {}
for tn in ([] if os.path.exists("boot_fits.json") else TIERS + ["pooled"]):
    sub = long if tn == "pooled" else long[long.tier == tn]
    ids = sub.id.unique(); grp = {i: g for i, g in sub.groupby("id")}
    taus, betas = [], []
    for _ in range(100):
        pick = rng.choice(ids, len(ids)); s = pd.concat([grp[i] for i in pick])
        tau, b = fit(s.frac.values, np.log(s.t.values)); taus.append(tau); betas.append(b)
    tau, b = fit(sub.frac.values, np.log(sub.t.values))
    fits[tn] = dict(tau=round(float(tau),1), tau_lo=round(float(np.percentile(taus,2.5)),1), tau_hi=round(float(np.percentile(taus,97.5)),1),
                    beta=round(float(b),2), beta_lo=round(float(np.percentile(betas,2.5)),2), beta_hi=round(float(np.percentile(betas,97.5)),2))
    print(tn, fits[tn], flush=True)
if fits: json.dump(fits, open("boot_fits.json", "w"), indent=1)
# 3. R2 per horizon: bootstrap over test posts (fixed training fit)
df["postedAt"] = pd.to_datetime(df.postedAt, format="ISO8601"); split = (df.postedAt < pd.Timestamp("2026-01-01", tz="UTC")).values
def level_at(N):
    lv = np.zeros(len(df))
    for k in KS: lv = np.where((df[f"t{k}"] <= N) & df[f"t{k}"].notna(), k, lv)
    return lv
res = []
for N in [1,2,4,8,12,24,48,72,168]:
    lv = level_at(N); t_last = np.log1p(np.select([lv == k for k in KS[::-1]], [df[f"t{k}"] for k in KS[::-1]], default=N))
    X = pd.get_dummies(pd.Series(lv).astype(int), prefix="lv").astype(float); X["t_last"] = t_last; X["const"] = 1.0
    y = df.logF.values; ap = df.author_prior.fillna(0).values
    row = dict(N=N)
    for name, Xm, mask in [("early", X.values, np.ones(len(df), bool)), ("author", np.c_[np.ones(len(df)), ap], df.author_prior.notna().values), ("both", np.c_[X.values, ap], df.author_prior.notna().values)]:
        beta, *_ = np.linalg.lstsq(Xm[split & mask], y[split & mask], rcond=None)
        te = np.where(~split & mask)[0]; pred = Xm[te] @ beta; yt = y[te]
        r2s = []
        for _ in range(B):
            i = rng.choice(len(te), len(te)); r2s.append(1 - ((yt[i]-pred[i])**2).sum() / ((yt[i]-yt[i].mean())**2).sum())
        row[f"r2_{name}"] = round(float(1 - ((yt-pred)**2).sum()/((yt-yt.mean())**2).sum()),3); row[f"r2_{name}_lo"] = round(float(np.percentile(r2s,2.5)),3); row[f"r2_{name}_hi"] = round(float(np.percentile(r2s,97.5)),3)
    res.append(row); print(row, flush=True)
pd.DataFrame(res).to_csv("pred_summary_boot.csv", index=False)
