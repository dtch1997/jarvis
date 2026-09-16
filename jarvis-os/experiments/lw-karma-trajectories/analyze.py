import json, numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr
pd.set_option("display.width", 200)
KS = [2, 30, 45, 75, 125, 200]
rows = [json.loads(l) for l in open("posts.jsonl")]
df = pd.DataFrame(rows).drop_duplicates("_id")
print("raw", len(df))
df = df[~df.isEvent.fillna(False) & ~df.shortform.fillna(False) & ~df.draft.fillna(False)].copy()
print("after drop events/shortform/drafts", len(df))
df["postedAt"] = pd.to_datetime(df.postedAt)
df["F"] = df.baseScore.astype(float)
for k in KS:
    d = pd.to_datetime(df[f"scoreExceeded{k}Date"])
    t = (d - df.postedAt).dt.total_seconds() / 3600
    df[f"t{k}"] = t
neg = {k: int((df[f"t{k}"] < 0).sum()) for k in KS}
print("crossings before postedAt (clipped to 0):", neg)
for k in KS: df[f"t{k}"] = df[f"t{k}"].clip(lower=0)
# consistency
for k in KS[1:]:
    a = ((df.F >= k) & df[f"t{k}"].isna()).sum(); b = ((df.F < k) & df[f"t{k}"].notna()).sum()
    print(f"k={k}: final>={k} but no crossing date: {a}; crossed but final<{k} (fell back): {b}; ever crossed: {df[f't{k}'].notna().sum()}")
print("\nFinal karma quantiles:", df.F.quantile([.1,.25,.5,.75,.9,.95,.99]).round(0).to_dict())

# ---- 1. crossing-time distributions
print("\n== Hours to cross threshold (posts that ever cross) ==")
tab = []
for k in KS[1:]:
    t = df[f"t{k}"].dropna()
    tab.append(dict(k=k, n=len(t), **{f"p{p}": round(float(t.quantile(p/100)),1) for p in (10,25,50,75,90)}))
print(pd.DataFrame(tab).to_string(index=False))

# ---- 2. collapse test + parametric fit
# use posts with F>=30, age>=30d guaranteed by pull window; pairs (post, k) with k crossed and k<=F
long = []
for k in KS[1:]:
    m = df[f"t{k}"].notna() & (df.F >= k)
    long.append(pd.DataFrame(dict(id=df._id[m], F=df.F[m], k=k, t=df[f"t{k}"][m], frac=k/df.F[m])))
long = pd.concat(long); long = long[long.t > 0]
tiers = [(30,45),(45,75),(75,125),(125,200),(200,10**9)]
def tier(F):
    for lo,hi in tiers:
        if lo <= F < hi: return f"{lo}-{hi if hi<10**9 else 'inf'}"
long["tier"] = long.F.map(tier)
print("\n== Median hours to cross k, by final-karma tier (rows) — a 'universal' curve means same k/F ⇒ same time ==")
piv = long.pivot_table(index="tier", columns="k", values="t", aggfunc="median").round(1)
piv = piv.reindex([f"{lo}-{hi if hi<10**9 else 'inf'}" for lo,hi in tiers])
print(piv.to_string())
print("\n== Median k/F (fraction of final) at those crossings ==")
print(long.pivot_table(index="tier", columns="k", values="frac", aggfunc="median").round(2).reindex(piv.index).to_string())

# parametric: karma(t) = F * g(t); candidate g: weibull 1-exp(-(t/tau)^b); loglogistic 1/(1+(t/tau)^-b)
def inv_weib(frac, tau, b): return tau * (-np.log(1 - frac)) ** (1 / b)
def inv_ll(frac, tau, b): return tau * (frac / (1 - frac)) ** (1 / b)
def fit(sub, inv):
    fr = np.clip(sub.frac.values, 1e-3, 0.98); lt = np.log(sub.t.values)
    def loss(p):
        tau, b = np.exp(p); pred = np.log(inv(fr, tau, b)); return np.mean(np.abs(lt - pred))  # robust (LAD in log-time)
    r = minimize(loss, [np.log(24), 0.0], method="Nelder-Mead"); tau, b = np.exp(r.x); return tau, b, r.fun
print("\n== Parametric fit karma(t)=F*g(t), fitted on all (post,k) pairs; loss = median-ish |log t_obs - log t_pred| ==")
for name, inv in [("weibull", inv_weib), ("loglogistic", inv_ll)]:
    tau, b, L = fit(long, inv); print(f"{name}: tau={tau:.1f}h beta={b:.2f} mean|dlog t|={L:.2f}")
print("\n== Per-tier fits (log-logistic): does the timescale tau depend on final karma? ==")
for tname in piv.index:
    sub = long[long.tier == tname]
    if len(sub) < 50: continue
    tau, b, L = fit(sub, inv_ll); print(f"tier {tname:>8}: n_pairs={len(sub):5d} tau={tau:6.1f}h beta={b:.2f} fit={L:.2f}")
tau, b, _ = fit(long, inv_ll)
g = lambda t: 1 / (1 + (t / tau) ** (-b))
print("\nPooled log-logistic: fraction of final karma reached at", {f"{h}h": round(float(g(h)),2) for h in (1,3,6,12,24,48,72,168,336,720)})
# per-post shape check: ratio t75/t30 across tiers
sub = df[df.t30.notna() & df.t75.notna() & (df.t30>0)]
print("\nMedian t75/t30 ratio by tier:", sub.assign(tier=sub.F.map(tier)).groupby("tier").apply(lambda s: round(float((s.t75/s.t30).median()),2)).to_dict())

# ---- 3. prediction from first N hours
df = df.sort_values("postedAt").reset_index(drop=True)
# author prior: mean log-karma of the author's previous posts in the dataset (>=1 prior post)
df["logF"] = np.log(df.F.clip(lower=1) + 1)
prior = []; hist = {}
for uid, lf in zip(df.userId, df.logF):
    h = hist.get(uid); prior.append(np.mean(h) if h else np.nan); hist.setdefault(uid, []).append(lf)
df["author_prior"] = prior
LEVELS = [0] + KS
def level_at(N):
    lv = np.zeros(len(df))
    for k in KS:
        lv = np.where((df[f"t{k}"] <= N) & df[f"t{k}"].notna(), k, lv)
    return lv
HORIZONS = [1, 2, 4, 8, 12, 24, 48, 72, 168]
split = df.postedAt < pd.Timestamp("2026-01-01", tz="UTC")
res = []
print("\n== Prediction of final karma from highest threshold crossed by N hours ==")
for N in HORIZONS:
    lv = level_at(N); df["lv"] = lv
    df["t_last"] = np.log1p(np.select([lv == k for k in KS[::-1]], [df[f"t{k}"] for k in KS[::-1]], default=N))
    rho = spearmanr(lv, df.F).correlation
    X = pd.get_dummies(df.lv.astype(int), prefix="lv").astype(float); X["t_last"] = df.t_last; X["const"] = 1.0
    def ols_r2(X, y, mask_tr, mask_te):
        beta, *_ = np.linalg.lstsq(X[mask_tr].values, y[mask_tr].values, rcond=None)
        pred = X[mask_te].values @ beta; yt = y[mask_te].values
        return 1 - ((yt - pred) ** 2).sum() / ((yt - yt.mean()) ** 2).sum(), pred
    te = ~split
    r2_early, pred_early = ols_r2(X, df.logF, split, te)
    ap = df.author_prior.notna()
    Xa = pd.DataFrame(dict(const=1.0, ap=df.author_prior.fillna(0)))
    r2_author, _ = ols_r2(Xa, df.logF, split & ap, te & ap)
    Xb = X.copy(); Xb["ap"] = df.author_prior.fillna(0)
    r2_both, _ = ols_r2(Xb, df.logF, split & ap, te & ap)
    r2_early_ap, _ = ols_r2(X, df.logF, split & ap, te & ap)
    # calibration table
    cal = df.groupby(df.lv.astype(int)).F.agg(n="size", median="median", p10=lambda s: s.quantile(.1), p90=lambda s: s.quantile(.9),
                                              ge75=lambda s: (s>=75).mean(), ge125=lambda s: (s>=125).mean())
    res.append(dict(N=N, spearman=round(rho,3), r2_early=round(r2_early,3), r2_author=round(r2_author,3), r2_both=round(r2_both,3), r2_early_ap=round(r2_early_ap,3)))
    print(f"\n-- N={N}h: spearman(level, final)={rho:.3f}; test R² (log final): early={r2_early:.3f}, author-prior={r2_author:.3f}, both={r2_both:.3f} (early on same subset={r2_early_ap:.3f})")
    print(cal.round(2).to_string())
    cal.assign(N=N).to_csv(f"cal_{N}.csv")
R = pd.DataFrame(res); print("\n", R.to_string(index=False)); R.to_csv("pred_summary.csv", index=False)
long.to_csv("long.csv", index=False); df.to_csv("posts_clean.csv", index=False)
json.dump(dict(tau=tau, beta=b), open("fit.json","w"))
