# Empirical anchors: faithfulness, monitor accuracy, human throughput
(gathered 2026-09-08 by research subagent; each line: number — context — source)

## CoT faithfulness / unfaithfulness (U)
- 25% / 39% — Claude 3.7 Sonnet / DeepSeek R1 hint-mention rate when hint used — Anthropic Apr 2025, arxiv 2505.05410
- 41% / 19% — same, "unauthorized access" hint type
- >99% exploit vs <2% verbalize — RL reward-hack envs, 5/6 environments — same paper
- 28% (MMLU) / 20% (GPQA) — faithfulness plateau under outcome RL — same paper
- ~95% vs ~60% — GPT-4o monitor recall on systemic hacks, CoT vs action-only — OpenAI Mar 2025, arxiv 2503.11926
- ~0% — monitor recall after CoT optimization pressure (obfuscated reward hacking) — same
- +27pp — CoT monitoring adds on subtle sabotage; CoT can FOOL monitor on blatant — CoT Red-Handed, arxiv 2505.23575

## Monitorability trend evidence (both directions)
- Korbak et al. Jul 2025 (2507.11473): fragile-opportunity position paper; threats = RL scale, CoT process supervision, latent reasoning
- COCONUT Dec 2024 (2412.06769): latent reasoning works at small scale, no legible trace
- R1-Zero: pure RL → "poor readability, language mixing"; legibility reward added (2501.12948)
- COUNTER: "Monitoring Monitorability" Dec 2025 (2512.18311, ICML26 oral): RL at current scale does NOT materially reduce monitorability; longer CoTs MORE monitorable; monitor test-time compute helps
- COUNTER: "Pragmatic CoT Monitorability" Oct 2025 (2510.23966): when CoT is necessary, it's highly legible by default; evasion hard when CoT necessary (2507.05246)

## Human oversight throughput / cost (v_read)
- 238 wpm — adult non-fiction silent reading — Brysbaert 2019 meta-analysis (careful/study reading ~100-200 wpm)
- 150-500 LOC/hr review; defect discovery collapses >~450-500 LOC/hr — SmartBear/Cisco 2006
- median reviewed change = 24 LOC, 1 reviewer — Google ICSE-SEIP 2018
- AUC 0.65 @ ~103 min/transcript (human) vs AUC 0.87 (Gemini 2.5 Pro) — SHADE-Arena sabotage auditing, arxiv 2506.15740 ← KEY ANCHOR
- $50-100/hr base (+bonuses; ~$232/hr effective on RE-Bench) — METR baseliners; $69.50/hr mean US SWE (BLS 2024)
- ~$1855 per 8h human run vs ~$123 per 8h agent run (~15x) — RE-Bench Nov 2024

## AI-monitoring-AI (control) numbers
- 2% human audit budget convention — Greenblatt et al. control paper (2312.06942)
- safety/usefulness @2%: upfront audit 15/100, trusted monitor 62/97, +defer10 83/93, +defer20 92/83, untrusted monitor 79/96, trusted edit 92/94
- oversight success @400-Elo gap: 13.5% Mafia, 51.7% Debate, 10.0% Backdoor Code, 9.4% Wargames — Engels et al. 2504.18530

## Caveats
- OpenAI 95/60 + Anthropic <2% from hack-rich envs; absolute rates don't transfer
- Greenblatt %s are red-team-game win rates, not detection rates
- 2512.18311 + 2510.23966 cut against "RL already eroding legibility" at today's scale
