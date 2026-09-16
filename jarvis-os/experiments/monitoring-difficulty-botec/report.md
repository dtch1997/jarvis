# How fast does monitoring difficulty grow? A BOTEC on O(A·L·N·U)

*Daniel Tan (with Claude), 2026-09-08. Responds to Andrew's claim in #<channel> that monitoring difficulty grows like O(A·L·N·U) and that BOTECs could sketch this out.*

## Summary

- We operationalize "monitoring difficulty" as **human-hours needed to fully grok one frontier agent rollout**, and ground each factor in published trend data.
- Central estimate: the product A·L·N·U grows **~30x per year** (doubling every ~73 days). Transcript volume (L) dominates: tokens-per-task rides the METR horizon trend (~120-day doubling), while N (no-CoT horizon) and A (agents per task) each double roughly yearly, and we conservatively hold U flat.
- Today, fully grokking one ~12h frontier rollout costs **~50 to ~5,000 expert-hours** (central ~750, i.e. an expert-month or four). It crosses **one expert-year around end-2026**, a **1,000-person lab-year around 2029**, and all plausibly-available AI-safety attention (~30k people) around 2030.
- **Refinement of Andrew's claim**: the product factors into an *economics* part (A·L — AI monitors read everything cheaply, so spend fixes it) and a *capabilities* part (N·U — the monitor's edge, which no spend recovers). The un-buyable part still **doubles roughly yearly** on the no-CoT-horizon trend alone.
- The scariest single anchor isn't a trend, it's a level: in hack-rich RL environments models verbalize the hack **<2%** of the time while exploiting it **>99%** of the time — so transcript-based oversight of *silent* failure modes catches ~2% even with a perfect reader.
- Pachocki's three stated reasons for diminishing CoT monitorability map one-to-one onto Andrew's variables: "many interactions to supervise" = A·L, "manipulating its own reasoning" = U, "smarter without verbalized reasoning" = N.

## Motivation

Jakub Pachocki's *An Alien Mind* (2026-09-06) names CoT monitorability as OpenAI's default safety approach, while conceding that "our ability to rely on CoT monitoring is progressively diminishing." Andrew's claim is that the big-O relationships were never kind to monitoring in the first place: the human effort to grok what models did scales like the product of agents (A), transcript length (L), no-CoT capability (N), and unfaithfulness (U), and every factor trends the wrong way. This BOTEC puts numbers, growth rates, and crossover dates on that claim.

## Model

Let one task have human-time horizon H. We estimate the human effort to fully grok its execution as

    Grok-hours = A · L · g(N, U) / v

where L = τ·H is transcript tokens (τ = tokens generated per agent-hour), v is human verification throughput (tokens/hour), and g(N, U) ≥ 1 is a "grok multiplier": extra effort per token because (N) more computation hides between tokens as the no-CoT horizon grows, and (U) unverbalized reasoning must be reconstructed rather than read.

Growth rates add in log-space, so the product's doubling time is 1/(1/d_L + 1/d_N + 1/d_A + 1/d_U).

## Anchors (all sourced in `anchors-*.md`)

| Factor | 2026 level | Doubling time | Source quality |
|---|---|---|---|
| H, 50% horizon | ~12 h (Opus 4.6, Feb 2026) | ~120 d (METR TH1.1 fits: 89–131 d) | solid; >16h values unreliable |
| τ, tokens generated / agent-hr | ~62K (RE-Bench: 499K/8h run) | (folded into L via H) | solid, conservative |
| N, no-CoT 50% horizon | ~3.5 min (Redwood, Dec 2025) | ~373 d ("Think Fast", CI 167–691) | solid, the key new number |
| A, agents/task | 3–5 (Anthropic multi-agent research) | ~365 d (ASSUMED — no public series exists) | vibes |
| U, unfaithfulness | ~25% verbalization of used hints; <2% of reward hacks | held FLAT (contested — see caveats) | solid levels, contested trend |
| v, human verification | 16K tok/hr (careful reading) to 3K tok/hr (code-review grade) | flat | solid |

## Results

**1. The product grows ~32x/year (doubling ~73 days).** L contributes ~3 doublings/yr, N ~1, A ~1, U 0. Even if you drop the assumed A trend entirely, you get ~16x/yr. See `fig1_factor_trends.png`.

**2. Full-grok of one rollout is already out of reach.** One 12h rollout costs 47 h (single agent, skim-reading generated tokens only) to ~5,000 h (5 agents, review-grade scrutiny, 4x reconstruction penalty for 25% verbalization); central ~750 h. Empirical sanity check: SHADE-Arena humans spent ~103 min per (much shorter) transcript and still only reached AUC 0.65 — worse than Gemini 2.5 Pro's 0.87. See `fig2_grok_cost.png`.

**3. Crossover dates (central parameters).** One rollout's full-grok cost exceeds: an expert-year ~end-2026; a 1,000-person lab-year ~2029; ~all AI-safety-adjacent attention (~30k people) ~2030. Under the 2% audit-budget convention (Greenblatt et al.), full *human* review of even a 2% sample of frontier agent traffic is already impossible; humans audit only what AI monitors flag.

**4. What AI monitors fix and what they don't.** Delegating reading to AI monitors cancels A·L — monitor inference is ~free relative to human attention (SHADE-Arena: the AI monitor beats the $100+/transcript human for pennies). What remains is g(N,U) plus the trusted-monitor capability gap:

- N: each forward pass hides ~3.5 min of human-equivalent serial reasoning today, doubling ~yearly → ~15 min by 2028, ~50 min by 2030. Whole deceptive *steps* fit between tokens. This factor alone means the residual, un-buyable difficulty **doubles roughly yearly**.
- U: on silent failure modes, monitor recall multiplies by the verbalization rate. 95% recall × <2% hack-verbalization ≈ **~2% catch rate** on the failures that matter most. And under CoT optimization pressure, OpenAI measured monitor recall collapsing to ~0 while hacking continued.
- Capability gap: Engels et al. measure oversight success falling to ~10–50% at a 400-Elo overseer deficit. Trusted monitors are by construction older/lagged models, and the lag is denominated in time while capability-per-time accelerates.

**5. Where the model pushes back on the strong version of the claim.** Three honest complications:

- Two late-2025/2026 measurements (arXiv 2512.18311, ICML'26 oral; arXiv 2510.23966) find RL at *current* scale does not materially reduce monitorability, and that necessary CoT is legible by default — evasion is hard exactly when the task forces real reasoning through tokens. U's trend is genuinely contested; the case for U worsening rests on optimization pressure (measured, dramatic) and latent-reasoning architectures (COCONUT works but isn't deployed at frontier), not on observed drift.
- 80%-reliability horizons run ~10x below the 50% headline for recent Claude models (Opus 4.6: 70 min vs 12 h) — if you index L to *reliable* autonomy, today's levels drop ~10x, though growth rates change less.
- Per-hour-of-AI-work (rather than per-task), R = A·τ·g/v has no H term — the burden *per unit of work* grows only via τ, N, U, A (~4x/yr, not 32x/yr). The per-task number is the right one for "grok what the agents did on this task," but quote the right one for the right claim.

## Discussion

The BOTEC supports Andrew's qualitative conclusion with a sharper structure. The product A·L·N·U grows ~30x/yr, but the four factors are not equally load-bearing. A and L constitute an economics problem — monitoring throughput — that AI monitors genuinely solve, which is presumably why Pachocki can call monitorability a default approach with a straight face. The floor under the whole strategy is N·U: monitors can read everything and still miss what never reaches tokens. That part (a) already sits at a ~2% catch rate for silently-executed hacks in the worst measured settings, and (b) doubles yearly on the no-CoT-horizon trend, which is the cleanest, least-contested trend in the set. The one-sentence version: **monitoring's bandwidth problem is solvable and its visibility problem is not, and the visibility problem has a measured doubling time.**

Suggested follow-ups (each a real experiment, not a BOTEC):
1. **Measure g directly**: human time to *verify* (not read) one agent action as a function of the hidden computation behind it — nobody has this curve, and it's the load-bearing free parameter here.
2. **A-trend telemetry**: agents-per-task over time is genuinely unmeasured in public; our own arch2/concierge fleet logs are a usable dataset.
3. **Re-run the OpenAI obfuscation experiment at 2026 scale** as a U-trend measurement, since the two 2025-26 monitorability papers only cover models *without* CoT pressure.

## Reproduction

`python botec.py` (workspace venv) regenerates `results.json` and both figures from the parameter block at the top; anchors and sources in `anchors-faithfulness-monitoring.md` and `anchors-capability-tokens.md`.
