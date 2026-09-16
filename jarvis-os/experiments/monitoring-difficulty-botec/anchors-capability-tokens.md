# Empirical anchors: time horizons, tokens, agents
(gathered 2026-09-08 by research subagent; each line: number — context — source)

## Time horizon (H) — METR
- 50% horizon doubling ~207d (2019-2025 all-time) — Kwa et al. 2503.14499
- TH1.1 re-analysis: since-2023 ~131d; since-2024 ~89d; 2024-2026 fit ~105d (R^2=.98) — metr.org/blog/2026-1-29-time-horizon-1-1
- GPT-5: ~2h17m (Aug 2025); Opus 4.5: ~4h49m (Dec 2025); Opus 4.6: ~12h (719min, Feb 2026; ~7h private-tasks-only); Mythos preview: >=16h, CI 8.5-55h (May 2026, suite saturated)
- 80% horizons: classic 4-6x below 50%; late-2025 plateau 27-32min; Opus 4.6 80% = 70min → 50/80 gap now ~10x for Claude models
- CAVEAT: >16h measurements unreliable (~5 of 228 tasks are 16h+)

## Tokens per task (L)
- RE-Bench: ~29M input + 499K output tokens per 8h agent run (~$123) → ~62K generated + ~3.7M read per agent-hour (derived)
- MALT corpus (24K runs): successful runs ~300K tokens; failed runs 2.58M avg (8.6x); 90% of $ on failed runs — 2604.24658
- SWE-bench agentic ≈ 1000x chat tokens; 30x same-task variance — 2604.22750
- Anthropic multi-agent research: agents 4x chat, multi-agent 15x chat; tokens explain 80% of perf variance — Anthropic eng blog Jun 2025
- Expenditure horizon: frontier absorbs $2.3-3.3K/task productively (Opus 4.8/GPT-5.5) vs $0 a year prior — metr.org 2026-07-21
- ARC-AGI o3: 33M tokens/task low-compute; 172x high-compute — arcprize Dec 2024

## No-CoT horizon (N)
- Opus 4.5 no-CoT 50% math horizon: 3.5 min (Gemini 3 Pro 3.8, G2.5P 2.7); doubling ~9mo; with-CoT comparable math = hours (~50-100x gap) — Redwood blog Dec 2025
- "Think Fast" 2606.07157 (Aug 2026): no-CoT doubling 373d [167-691] vs ~182d with-CoT; GPT-5.5 no-CoT >3min; reasoning-token horizon >1500 tok (→~12K by 2030); doubling no-CoT horizon costs ~4.2x params
- Net today: with-CoT ~12h vs no-CoT ~3.5min ≈ 200x gap, widening (derived)

## Agents per task (A)
- Anthropic research system: orchestrator + 3-5 parallel subagents, +90.2% over single-agent, 15x tokens — Jun 2025
- Devin fleets / AlphaEvolve populations / co-scientist tournaments: real but counts unpublished
- AlphaCode: 1000+ samples/task; o3 ARC 1024 samples — proto-multi-agent
- NO public agent-count-over-time series exists — A trend must be assumed/parametric

## Caveats
- >16h horizon numbers are extrapolation
- 80% (reliable) horizons grew much slower than 50% headline
- token counts input-dominated (context re-reads); generated-only is 50-100x smaller
