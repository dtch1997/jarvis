"""Build the LW karma-trajectories report page (inline SVG charts) from analysis outputs."""
import json, math, html
import pandas as pd, numpy as np
long = pd.read_csv("long.csv"); fits = json.load(open("tier_fits.json")); pred = pd.read_csv("pred_summary.csv")
df = pd.read_csv("posts_clean.csv")
bm = json.load(open("boot_medians.json")); bf = json.load(open("boot_fits.json")); predb = pd.read_csv("pred_summary_boot.csv")
TIERS = ["30-45", "45-75", "75-125", "125-200", "200-inf"]
TLABEL = {"30-45": "30–44", "45-75": "45–74", "75-125": "75–124", "125-200": "125–199", "200-inf": "200+"}
KS = [30, 45, 75, 125, 200]
N = len(df); n30 = int((df.F >= 30).sum())

# ---------- SVG helpers ----------
W, H = 720, 400; ML, MR, MT, MB = 56, 20, 16, 44
def sx(x, x0, x1, log=True):
    if log: x, x0, x1 = math.log10(x), math.log10(x0), math.log10(x1)
    return ML + (x - x0) / (x1 - x0) * (W - ML - MR)
def sy(y, y0, y1): return MT + (1 - (y - y0) / (y1 - y0)) * (H - MT - MB)
def axes(xt, yt, x0, x1, y0, y1, xlab, ylab, xlog=True, xfmt=str, yfmt=str):
    s = []
    for v in yt:
        y = sy(v, y0, y1); s.append(f'<line class="grid" x1="{ML}" x2="{W-MR}" y1="{y:.1f}" y2="{y:.1f}"/>')
        s.append(f'<text class="tick" x="{ML-8}" y="{y+4:.1f}" text-anchor="end">{yfmt(v)}</text>')
    for v in xt:
        x = sx(v, x0, x1, xlog); s.append(f'<line class="grid" y1="{MT}" y2="{H-MB}" x1="{x:.1f}" x2="{x:.1f}"/>')
        s.append(f'<text class="tick" x="{x:.1f}" y="{H-MB+16}" text-anchor="middle">{xfmt(v)}</text>')
    s.append(f'<line class="axis" x1="{ML}" x2="{W-MR}" y1="{H-MB}" y2="{H-MB}"/>')
    s.append(f'<text class="lab" x="{(ML+W-MR)/2}" y="{H-6}" text-anchor="middle">{xlab}</text>')
    s.append(f'<text class="lab" transform="translate(14,{(MT+H-MB)/2}) rotate(-90)" text-anchor="middle">{ylab}</text>')
    return "\n".join(s)
def line(pts, cls, dash=False):
    d = " ".join(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    return f'<path class="{cls}" d="{d}"{" stroke-dasharray=\"6 5\"" if dash else ""}/>'
def dots(pts, cls, tips):
    return "\n".join(f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="4.5"><title>{html.escape(t)}</title></circle>' for (x, y), t in zip(pts, tips))
def legend(items, x=ML+10, y=MT+10):
    s = []
    for i, (cls, lab) in enumerate(items):
        yy = y + i * 18
        s.append(f'<line class="{cls}" x1="{x}" x2="{x+22}" y1="{yy}" y2="{yy}"/><text class="leg" x="{x+28}" y="{yy+4}">{lab}</text>')
    return "\n".join(s)
def vbar(x, y0, y1, cls): return f'<line class="{cls} eb" x1="{x:.1f}" x2="{x:.1f}" y1="{y0:.1f}" y2="{y1:.1f}"/>'
def hbar(y, x0, x1, cls): return f'<line class="{cls} eb" y1="{y:.1f}" y2="{y:.1f}" x1="{x0:.1f}" x2="{x1:.1f}"/>'
def svg(body, title): return f'<figure><svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)}">{body}</svg><figcaption>{title}</figcaption></figure>'
hrs = lambda v: f"{v:g}h" if v < 48 else (f"{v/24:g}d" if v < 720 else "30d")


# ---------- Fig 1 (direct): karma threshold on x, median hours to cross on y ----------
b = [axes([30,45,75,125,200], [math.log10(v) for v in (1,3,10,24,72)], 25, 240, math.log10(1), math.log10(150), "karma threshold (log)", "median hours to cross it (log)", xfmt=str, yfmt=lambda v: hrs(round(10**v)))]
def syl(v): return sy(math.log10(v), math.log10(1), math.log10(150))
for i, tn in enumerate(TIERS):
    rows = [(k, bm[f"{tn}|{k}"]) for k in KS if f"{tn}|{k}" in bm]
    pts = [(sx(k, 25, 240), syl(r["t_med"])) for k, r in rows]
    for (x, y), (k, r) in zip(pts, rows): b.append(vbar(x, syl(r["t_lo"]), syl(r["t_hi"]), f"s{i+1}"))
    b.append(line(pts, f"s{i+1}")); b.append(dots(pts, f"s{i+1}", [f"final {TLABEL[tn]}: median {r['t_med']:.1f}h to cross {k} (95% CI {r['t_lo']:.1f}–{r['t_hi']:.1f}h, n={r['n']})" for k, r in rows]))
b.append(legend([(f"s{i+1}", f"final karma {TLABEL[t]}") for i, t in enumerate(TIERS)], x=ML+12, y=MT+14))
fig0 = svg("\n".join(b), "Figure 1. Median hours to cross each karma threshold, by the post's final karma. Bars are 95% bootstrap intervals on the median (mostly narrower than the dots). The same threshold is crossed in a fraction of the time by posts that end high.")

# ---------- Fig 1: hours to reach a given fraction of final karma, by tier ----------
b = [axes([1,3,10,30,100,300,1000], [0.1,0.2,0.3,0.5,0.7,1.0], 1, 2000, 0, 1, "median hours after posting to cross the threshold (log)", "threshold ÷ final karma", xfmt=hrs, yfmt=lambda v: f"{v:.1f}")]
for i, tn in enumerate(TIERS):
    sub = long[long.tier == tn]
    med = sub.groupby("k").agg(t=("t","median"), frac=("frac","median"), n=("t","size")).reset_index()
    med = med[med.n >= 30].sort_values("k")
    pts = [(sx(r.t, 1, 2000), sy(r.frac, 0, 1)) for r in med.itertuples()]
    for (x, y), r in zip(pts, med.itertuples()):
        e = bm[f"{tn}|{int(r.k)}"]; b.append(hbar(y, sx(e["t_lo"], 1, 2000), sx(e["t_hi"], 1, 2000), f"s{i+1}"))
    b.append(line(pts, f"s{i+1}")); b.append(dots(pts, f"s{i+1}", [f"final {TLABEL[tn]}: crosses {int(r.k)} karma after {r.t:.1f}h (median of {r.n} posts); {r.frac:.2f} of final" for r in med.itertuples()]))
b.append(legend([(f"s{i+1}", f"final karma {TLABEL[t]}") for i, t in enumerate(TIERS)], x=W-MR-190, y=H-MB-100))
fig1 = svg("\n".join(b), "Figure 2. To reach the same fraction of its final karma, a post that ends at 200+ takes 3–5× longer than one that ends at 30–44. Same data as Figure 1, re-expressed as fraction of final karma; horizontal bars are 95% bootstrap intervals.")

# ---------- Fig 2: fitted fraction-of-final curves ----------
b = [axes([1,3,10,30,100,300,720], [0,0.25,0.5,0.75,1.0], 1, 720, 0, 1, "hours after posting (log)", "fraction of final karma (fitted)", xfmt=hrs, yfmt=lambda v: f"{v:.2f}")]
xs = np.logspace(0, math.log10(720), 80)
for i, tn in enumerate(TIERS):
    tau, be = fits[tn]["tau"], fits[tn]["beta"]
    b.append(line([(sx(x, 1, 720), sy(1/(1+(x/tau)**(-be)), 0, 1)) for x in xs], f"s{i+1}"))
tau, be = fits["pooled"]["tau"], fits["pooled"]["beta"]
b.append(line([(sx(x, 1, 720), sy(1/(1+(x/tau)**(-be)), 0, 1)) for x in xs], "s0", dash=True))
for h in (24, 168):
    x = sx(h, 1, 720); b.append(f'<line class="mark" x1="{x:.1f}" x2="{x:.1f}" y1="{MT}" y2="{H-MB}"/>')
b.append(legend([(f"s{i+1}", f"final {TLABEL[t]}  (τ={fits[t]['tau']}h)") for i, t in enumerate(TIERS)] + [("s0", f"all posts pooled (τ={fits['pooled']['tau']}h)")], x=W-MR-230, y=H-MB-120))
fig2 = svg("\n".join(b), "Figure 3. Log-logistic fits karma(t) = F · 1/(1+(t/τ)^−β). The shape is shared (β ≈ 0.8–1.0); the half-life τ grows from 6h to 25h with final karma. Vertical marks: 24h and 7d. Per-tier τ intervals are in the table below.")

# ---------- Fig 3: predictability vs horizon ----------
b = [axes([1,2,4,8,24,72,168], [0,0.2,0.4,0.6,0.8], 1, 168, 0, 0.9, "hours of karma history used (log)", "out-of-sample R² on log final karma", xfmt=hrs, yfmt=lambda v: f"{v:.1f}")]
for i, (col, lab) in enumerate([("r2_early", "highest threshold crossed so far"), ("r2_author", "author's past posts only"), ("r2_both", "both")]):
    pts = [(sx(r.N, 1, 168), sy(getattr(r, col), 0, 0.9)) for r in predb.itertuples()]
    for (x, y), r in zip(pts, predb.itertuples()): b.append(vbar(x, sy(getattr(r, col+"_lo"), 0, 0.9), sy(getattr(r, col+"_hi"), 0, 0.9), f"s{i+1}"))
    b.append(line(pts, f"s{i+1}")); b.append(dots(pts, f"s{i+1}", [f"{lab}, {int(r.N)}h: R²={getattr(r, col):.2f} (95% CI {getattr(r, col+'_lo'):.2f}–{getattr(r, col+'_hi'):.2f})" for r in predb.itertuples()]))
b.append(legend([("s1", "highest threshold crossed so far"), ("s2", "author's past posts only"), ("s3", "both")], x=ML+12, y=MT+14))
fig3 = svg("\n".join(b), "Figure 4. Predicting a post's 1-month log-karma from what it has crossed by hour N (trained on posts before 2026-01, tested on 2026 posts; bars are 95% bootstrap intervals over the 2,700 test posts). By 24h the early signal explains two-thirds of the variance; author history adds little after that.")

# ---------- Calibration tables ----------
def caltab(N):
    c = pd.read_csv(f"cal_{N}.csv").rename(columns={"lv": "level"})
    rows = []
    for r in c.itertuples():
        lab = {0: "below 2", 2: "≥ 2 (only)"}.get(int(r.level), f"≥ {int(r.level)}")
        rows.append(f"<tr><td>{lab}</td><td>{int(r.n):,}</td><td>{r.median:.0f}</td><td>{r.p10:.0f} – {r.p90:.0f}</td><td>{100*r.ge75:.0f}%</td><td>{100*r.ge125:.0f}%</td></tr>")
    return f'<table><thead><tr><th>highest threshold crossed by {N}h</th><th>posts</th><th>median final</th><th>10th–90th pct</th><th>P(final ≥ 75)</th><th>P(final ≥ 125)</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
cross = []
for k in KS:
    t = df[f"t{k}"].dropna(); t = t[t > 0]
    cross.append(f"<tr><td>{k}</td><td>{len(t):,}</td><td>{t.quantile(.1):.1f}</td><td>{t.quantile(.5):.1f}</td><td>{t.quantile(.9):.0f}</td></tr>")
crosstab = f'<table><thead><tr><th>karma threshold</th><th>posts that reach it</th><th>10th pct (h)</th><th>median (h)</th><th>90th pct (h)</th></tr></thead><tbody>{"".join(cross)}</tbody></table>'
fitrows = "".join(f"<tr><td>{TLABEL.get(t,'all posts pooled')}</td><td>{fits[t]['tau']} <span class=ci>[{bf[t]['tau_lo']}–{bf[t]['tau_hi']}]</span></td><td>{fits[t]['beta']} <span class=ci>[{bf[t]['beta_lo']}–{bf[t]['beta_hi']}]</span></td><td>{fits[t]['h24']:.2f}</td><td>{fits[t]['h72']:.2f}</td><td>{fits[t]['h168']:.2f}</td></tr>" for t in TIERS + ["pooled"])
fittab = f'<table><thead><tr><th>final karma</th><th>τ (hours) [95% CI]</th><th>β [95% CI]</th><th>fraction by 24h</th><th>by 3d</th><th>by 7d</th></tr></thead><tbody>{fitrows}</tbody></table>'

page = f"""<title>LessWrong Karma Clock</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{ color-scheme: light; --bg:#f6f5f1; --panel:#fdfcf9; --ink:#1b1d22; --ink2:#575c66; --ink3:#8a8f99; --rule:#dedbd3; --grid:#e9e6de;
  --s0:#6b7280; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --mark:#c9c4b6; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark; --bg:#17181b; --panel:#1f2024; --ink:#ecebe6; --ink2:#b9b8b0; --ink3:#83827c; --rule:#33353a; --grid:#2a2c31;
  --s0:#9ca3af; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --mark:#4a4c52; }} }}
:root[data-theme="dark"] {{ color-scheme: dark; --bg:#17181b; --panel:#1f2024; --ink:#ecebe6; --ink2:#b9b8b0; --ink3:#83827c; --rule:#33353a; --grid:#2a2c31;
  --s0:#9ca3af; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --mark:#4a4c52; }}
body {{ background: var(--bg); color: var(--ink); font-family: "IBM Plex Sans", system-ui, sans-serif; font-size: 16px; line-height: 1.55; }}
main {{ max-width: 760px; margin: 0 auto; padding: 40px 20px 80px; }}
h1 {{ font-family: "Source Serif 4", Georgia, serif; font-weight: 600; font-size: 2.1rem; line-height: 1.15; margin: 0 0 6px; text-wrap: balance; }}
h2 {{ font-family: "Source Serif 4", Georgia, serif; font-weight: 600; font-size: 1.35rem; margin: 44px 0 10px; text-wrap: balance; }}
p {{ max-width: 66ch; margin: 0 0 14px; }}
.eyebrow {{ font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--ink3); margin-bottom: 10px; }}
.summary {{ background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 18px 22px; margin: 22px 0 8px; }}
.summary p {{ margin: 0 0 8px; }} .summary p:last-child {{ margin: 0; }}
figure {{ margin: 22px 0 26px; }} svg {{ width: 100%; height: auto; display: block; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; }}
figcaption {{ font-size: .88rem; color: var(--ink2); margin-top: 8px; max-width: 70ch; }}
.grid {{ stroke: var(--grid); stroke-width: 1; }} .axis {{ stroke: var(--rule); stroke-width: 1; }} .mark {{ stroke: var(--mark); stroke-width: 1; stroke-dasharray: 3 4; }}
.tick, .lab, .leg {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px; fill: var(--ink2); }} .lab {{ fill: var(--ink3); }} .leg {{ fill: var(--ink); font-family: "IBM Plex Sans", sans-serif; font-size: 12px; }}
path.s0, path.s1, path.s2, path.s3, path.s4, path.s5 {{ fill: none; stroke-width: 2; stroke-linejoin: round; }}
line.s0, line.s1, line.s2, line.s3, line.s4, line.s5 {{ stroke-width: 2.5; }}
circle.s1, circle.s2, circle.s3, circle.s4, circle.s5 {{ stroke: var(--panel); stroke-width: 2; }}
.s0 {{ stroke: var(--s0); fill: var(--s0); }} .s1 {{ stroke: var(--s1); fill: var(--s1); }} .s2 {{ stroke: var(--s2); fill: var(--s2); }} .s3 {{ stroke: var(--s3); fill: var(--s3); }} .s4 {{ stroke: var(--s4); fill: var(--s4); }} .s5 {{ stroke: var(--s5); fill: var(--s5); }}
line.eb {{ stroke-width: 1.5; opacity: .75; }} .ci {{ color: var(--ink3); font-size: .8em; }}
.tw {{ overflow-x: auto; margin: 12px 0 20px; }}
table {{ border-collapse: collapse; width: 100%; font-size: .9rem; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: right; padding: 7px 10px; border-bottom: 1px solid var(--rule); white-space: nowrap; }} th:first-child, td:first-child {{ text-align: left; }}
th {{ font-weight: 500; color: var(--ink2); font-size: .8rem; letter-spacing: .03em; }}
code {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .88em; }}
.note {{ font-size: .88rem; color: var(--ink2); }}
</style>
<main>
<div class="eyebrow">LessWrong GraphQL · {N:,} posts · Aug 2023 – Aug 2026</div>
<h1>How fast does a LessWrong post earn its karma?</h1>
<p class="note">Karma trajectories reconstructed from the six threshold-crossing timestamps LessWrong stores per post (when it first passed 2, 30, 45, 75, 125 and 200 karma), plus its karma today. Individual votes are not public. Every post is at least one month old, so "final" means karma at ≥30 days.</p>

<div class="summary">
<p><strong>Shape is shared, speed is not.</strong> Karma accrues like <code>F · t/(t+τ)</code>, a hyperbolic saturation with a heavy tail. But the half-life τ is not universal: it stretches from about 6 hours for posts that end at 30–44 karma to about 25 hours for posts that end above 200. Big posts are not just faster versions of small posts; they keep collecting for longer.</p>
<p><strong>Early karma predicts final karma well.</strong> Knowing only the highest threshold a post has crossed after 24 hours explains about two-thirds of the variance in log final karma on held-out 2026 posts. After 4 hours it explains under half; after 1 hour about a fifth. The author's track record explains ~37% on its own and adds little once a day of data is in.</p>
<p><strong>Rules of thumb.</strong> A post that has crossed 75 karma within 4 hours has a 96% chance of finishing above 125 (median 222). A post still under 30 karma after 24 hours has under a 1% chance of finishing above 75 (median 13).</p>
</div>

<h2>1. When posts cross each threshold</h2>
<p>Among the {n30:,} posts that ever reach 30 karma, the median crossing comes about 8 hours after posting, but the spread is wide: a tenth of them take longer than five days. Higher thresholds are slower and even more spread out.</p>
<div class="tw">{crosstab}</div>

<h2>2. Is there a universal curve?</h2>
<p>The direct view first. Figure 1 plots, for each final-karma tier, the median hours needed to cross each karma threshold. Posts that end high cross every threshold sooner: 30 karma takes about 31 hours for a post that ends at 30–44, 8 hours for one that ends at 45–74, and 1.5 hours for one that ends above 200. The 95% intervals on those medians are narrow; the ordering is not in doubt.</p>
{fig0}
<p>If every post followed one curve <code>karma(t) = F · g(t)</code> with the same <code>g</code>, then reaching a given <em>fraction</em> of final karma would take the same time regardless of <code>F</code>. Figure 2 re-expresses Figure 1 that way, and it does not hold: a 200+ post takes about 20 hours to reach half of its final karma, a 75–124 post about 9.</p>
{fig1}
<p>Fitting a two-parameter log-logistic curve per tier (Figure 3) makes the picture concrete. The exponent β sits in a narrow band (0.78–0.96), so the <em>shape</em> is close to universal, and it is close to the simplest hyperbola (β = 1). The timescale τ grows monotonically with final karma, and the bootstrap intervals on τ (over posts) do not overlap between neighbouring tiers except the lowest two. The fit is loose at the level of individual posts: the typical residual is a factor of e in time, because posting hour, weekday, and frontpage promotion all shift a post's clock.</p>
{fig2}
<div class="tw">{fittab}</div>
<p>Two consequences. First, "fraction of final karma at 24 hours" is not one number: it is about 79% for modest posts and 49% for the biggest ones. Second, since the shape is hyperbolic rather than exponential, the vote rate decays roughly as <code>1/t²</code> late on rather than dropping off a cliff, which is why a tenth of posts cross their thresholds days or weeks after posting.</p>

<h2>3. Predicting final karma from the first N hours</h2>
<p>The observation available at hour N is coarse: the highest of the six thresholds the post has crossed, and when it crossed it. Figure 4 shows how much of the variance in log final karma this explains, trained on posts before 2026 and tested on 2026 posts, against a baseline that only knows the author's past posts.</p>
{fig3}
<p>The calibration tables give the practical version: given what a post has crossed by hour N, what does it end up at?</p>
<h3 style="font-size:1rem;margin:18px 0 4px">After 4 hours</h3>
<div class="tw">{caltab(4)}</div>
<h3 style="font-size:1rem;margin:18px 0 4px">After 24 hours</h3>
<div class="tw">{caltab(24)}</div>
<h3 style="font-size:1rem;margin:18px 0 4px">After 72 hours</h3>
<div class="tw">{caltab(72)}</div>

<h2>Caveats and what would sharpen this</h2>
<p>The trajectory data is interval-censored: between thresholds the karma is unknown, and nothing below 30 is observed except the self-vote at 2. Roughly half of the 2-karma crossings predate publication (the author's own vote on the draft), so those are clipped to zero. About 2% of threshold crossings are later reversed by downvotes. Final karma is today's karma, so older posts had longer to mature, but the fitted curves say less than 1% arrives after day 30.</p>
<p>An hourly poller snapshotting <code>baseScore</code> for posts under 45 days old would replace the six-point trajectories with proper curves within a month and let the prediction use continuous karma rather than a threshold band. The pull and analysis scripts are in <code>jarvis-os/experiments/lw-karma-trajectories/</code>.</p>
</main>
"""
open("lw-karma-clock.html", "w").write(page); print("wrote", len(page))
