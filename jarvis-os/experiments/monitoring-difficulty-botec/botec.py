"""BOTEC: how fast does monitoring difficulty grow? (Andrew's O(A*L*N*U) claim)

Every parameter cites an anchor in anchors-*.md. Run: python botec.py
Outputs: results.json, fig1_factor_trends.png, fig2_grok_cost.png
"""
import json, math

try:
    import xy.pyplot as plt
    BACKEND = "xy"
except Exception:
    import matplotlib.pyplot as plt
    BACKEND = "matplotlib"

# ---------------- anchors (2026-09 baseline) ----------------
P = dict(
    # H: 50% time horizon, hours (Opus 4.6, Feb 2026, METR TH1.0)
    H_2026=12.0,
    dbl_H_days=120.0,        # METR 2024-2026 fits: 89-131d; central 120
    # tokens GENERATED per agent-hour (RE-Bench: 499K/8h run)
    tau_gen=62_000.0,
    tau_total=3_700_000.0,   # incl. input/context stream (29M/8h)
    # human verification throughput, tokens/hour
    v_skim=16_000.0,         # 200 wpm careful reading * ~1.33 tok/word (Brysbaert)
    v_review=3_000.0,        # ~300 LOC/hr code-review-grade * ~10 tok/LOC (SmartBear/Cisco)
    # A: agents per task (Anthropic multi-agent research: 3-5 + orchestrator)
    A_2026=3.0,
    dbl_A_days=365.0,        # ASSUMED - no public trend exists
    # N: no-CoT 50% horizon, minutes (Redwood Dec 2025: Opus 4.5 = 3.5 min)
    N_2026_min=3.5,
    dbl_N_days=373.0,        # "Think Fast" 2606.07157 [CI 167-691]
    # U: unfaithfulness. Verbalization rate ~25% (Anthropic 2505.05410);
    # trend contested at current scale (2512.18311) -> growth held FLAT (conservative)
    verbalize_rate=0.25,
    hack_verbalize_rate=0.02,
    audit_budget=0.02,       # AI-control convention (Greenblatt 2312.06942)
)

DPY = 365.0
def doublings_per_year(dbl_days): return DPY / dbl_days

# growth rates (doublings/year) of each factor of A*L*N*U, per-task normalization
rates = dict(
    L=doublings_per_year(P["dbl_H_days"]),  # tokens/task grows with horizon (L = tau*H)
    N=doublings_per_year(P["dbl_N_days"]),
    A=doublings_per_year(P["dbl_A_days"]),
    U=0.0,                                   # conservative: flat
)
r_product = sum(rates.values())
product_dbl_days = DPY / r_product
product_per_year = 2 ** r_product

# ---------------- BOTEC 1: full-grok cost of ONE rollout today ----------------
def grok_hours(A, tau, H, v, unfaith_mult=1.0):
    return A * tau * H / v * unfaith_mult

# unfaithfulness multiplier: if only ~25% of decision-relevant reasoning is
# verbalized, reconstructing the rest multiplies effort; floor it at 1 (just read)
u_mult = 1.0 / P["verbalize_rate"]

scenarios = {
    "low  (A=1, skim, gen-only tokens)":      grok_hours(1, P["tau_gen"], P["H_2026"], P["v_skim"]),
    "central (A=3, review-grade, gen-only)":  grok_hours(P["A_2026"], P["tau_gen"], P["H_2026"], P["v_review"]),
    "high (A=5, review-grade, x4 unfaithful)":grok_hours(5, P["tau_gen"], P["H_2026"], P["v_review"], u_mult),
}

# ---------------- BOTEC 2: crossover dates ----------------
central_2026 = scenarios["central (A=3, review-grade, gen-only)"]
thresholds = {
    "1 expert-week (40 h)": 40.0,
    "1 expert-year (2,000 h)": 2_000.0,
    "1,000-person lab-year (2M h)": 2_000_000.0,
    "all AI-safety-adjacent attention, ~30k ppl-yr (6e7 h)": 6e7,
}
def crossover_year(target, start=central_2026, t0=2026.7):
    if target <= start: return t0
    return t0 + math.log2(target / start) / r_product
crossovers = {k: round(crossover_year(v), 2) for k, v in thresholds.items()}

# ---------------- BOTEC 3: what AI monitors do and don't fix ----------------
# AI monitors cancel A*L (reading is ~free) but keep g(N,U):
r_residual = rates["N"] + rates["U"]         # doublings/yr of the un-buyable part
residual_per_year = 2 ** r_residual

# effective catch rate of transcript-based oversight on SILENT failure modes:
# monitor recall (95% with CoT, hack-rich env) * verbalization of hacks (<2%)
silent_catch = 0.95 * P["hack_verbalize_rate"]

results = dict(
    backend=BACKEND, params=P, rates_doublings_per_year=rates,
    product_doubling_days=round(product_dbl_days, 1),
    product_growth_per_year=round(product_per_year, 1),
    grok_hours_one_rollout_2026={k: round(v, 1) for k, v in scenarios.items()},
    crossover_dates=crossovers,
    residual_NU_growth_per_year=round(residual_per_year, 2),
    silent_failure_catch_rate=round(silent_catch, 3),
)
with open("results.json", "w") as f: json.dump(results, f, indent=2)
print(json.dumps(results, indent=2))

# ---------------- figures ----------------
years = [2024 + 0.1 * i for i in range(0, 71)]  # 2024-2031
def idx(year, r): return 2 ** (r * (year - 2026.7))

# Fig 1: factor trends, indexed to 1 at Sep 2026
fig1 = plt.figure(figsize=(8, 5))
for name, r, style in [
    ("L: transcript tokens/task (dbl 120d)", rates["L"], "-"),
    ("N: no-CoT horizon (dbl 373d)", rates["N"], "-"),
    ("A: agents/task (dbl 365d, assumed)", rates["A"], "--"),
    ("U: unfaithfulness (held flat)", rates["U"], ":"),
]:
    plt.plot(years, [idx(y, r) for y in years], style, label=name)
plt.plot(years, [idx(y, r_product) for y in years], "-", linewidth=3, color="black",
         label=f"product A*L*N*U (~{product_per_year:.0f}x/yr)")
plt.yscale("log")
plt.axvline(2026.7, color="gray", alpha=0.4)
plt.xlabel("year"); plt.ylabel("growth factor (Sep 2026 = 1, log scale)")
plt.title(f"Monitoring difficulty (A*L*N*U) grows ~{product_per_year:.0f}x/year;\ntranscript volume L dominates")
plt.legend(loc="upper left", fontsize=8); plt.tight_layout()
plt.savefig("fig1_factor_trends.png", dpi=150)
plt.close()

# Fig 2: human-hours to fully grok ONE frontier rollout
fig2 = plt.figure(figsize=(8, 5))
lo = scenarios["low  (A=1, skim, gen-only tokens)"]
hi = scenarios["high (A=5, review-grade, x4 unfaithful)"]
plt.fill_between(years, [lo * idx(y, r_product) for y in years],
                 [hi * idx(y, r_product) for y in years], alpha=0.25, label="low-high scenario band")
plt.plot(years, [central_2026 * idx(y, r_product) for y in years], "-", linewidth=2, label="central")
for label, hrs in thresholds.items():
    plt.axhline(hrs, color="gray", linestyle=":", alpha=0.7)
    plt.text(2024.05, hrs * 1.2, label, fontsize=7, color="gray")
plt.yscale("log")
plt.xlabel("year"); plt.ylabel("human-hours to fully grok one rollout (log)")
plt.title("Fully grokking ONE frontier agent rollout already costs ~an expert-month;\nit exceeds a 1,000-person lab-year around 2029")
plt.legend(loc="lower right", fontsize=8); plt.tight_layout()
plt.savefig("fig2_grok_cost.png", dpi=150)
plt.close()
print("figures written, backend =", BACKEND)
