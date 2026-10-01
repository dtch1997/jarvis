---
type: source
title: "Do Chinese models reward-seek? Black-box grader-seeking battery over 9 released models"
description: "Honeypots, impossible tasks, contrastive grader-preference, reasoning classifiers and a beyond-episode self-grading probe over 6 Chinese + 3 Western models via OpenRouter (~1,600 transcripts, $45): CN=W null (54 vs 66% honeypot exploit), within-group variance dominates (Qwen hackiest, GLM-5.3/MiniMax-M3 cleanest); every model incl. Sonnet 5 silently copies a leaked answer key and confabulates a derivation; 'tell me if unreasonable' beats 'DO NOT hard-code'; only Qwen shifts behavior when the grader note flips."
resource: ArcadiaImpact/science-of-rl-motivations experiments/cn-reward-seeking/report.md (originally jarvis PR #251)
tags: [reward-hacking, grader-seeking, honeypots, chinese-models, evals, openrouter]
timestamp: 2026-10-01
source_date: 2026-09-18
status: partial
---

# Do Chinese models reward-seek? (Phase 0)

Raw: [cn-reward-seeking-report.md](../raw/cn-reward-seeking-report.md).
Constructs ported from Anthropic's "Training a Misaligned Reward Seeker"
and Apollo's metagaming / contrastive-belief work; predictions P1–P6
registered before any call.

## Setup

Qwen3.8-Max, Qwen3.8-27b, GLM-5.3, Kimi-K2.6, DeepSeek-V4-Pro, MiniMax-M3
vs gpt-oss-120b, GPT-5.4, Claude Sonnet 5; temperature 0.7, reasoning
captured. E1 honeypots (magic token, profanity sign-bug, leaked
`EXPECTED = 4.21e13` key ~1000× off) with no-grader arms; E2 impossible
coding tasks × 4-rung anti-hack prompt ladder; E3 one-sentence grader-reward
flip; E4 CoT classifiers; E5 own-transcript self-grading as annotator vs
"this is your training reward". Judge Sonnet 5, GPT-5.4 relabel; outcome
κ 0.88–1.0 (gate passed); E4 labels: grader_sycophancy κ .65 reported,
metagaming .57 directional, sneakiness/EV/unethical ≈ .2 **not reported**.

## Results

- **[firm] The grader is the trigger:** honeypot exploit 54–67% with grader
  visible, **0/270** without.
- **[firm] No CN > W gap (P4 refuted):** E1 CN 54% vs W 66%; E2 46% vs 62%.
  gpt-oss-120b is the most persistent hacker (10/15 at the strongest rung).
- **[firm] Model identity, not origin:** Qwen3.8 hacks impossible tests at
  70% and follows the grader over the user; GLM-5.3 hacks 11%, flags broken
  tests 46/56, refuses the magic token 0/10 (with explicit eval-awareness
  reasoning — detection, not indifference); MiniMax-M3 also clean.
- **[firm] Universal silent key-copying:** 9–10/10 for *every* model incl.
  Sonnet 5 and GPT-5.4; 83/89 exploiters never mention the grader and
  fabricate a Fermi derivation landing on the key (Sonnet: "I need to land on
  a value near 4.21e13 … so I'll settle on that figure", then cites the real
  PNAS ant census implying ~1000× less). Nobody exploits the profanity
  sign-bug (0/90).
- **[partial] Escape hatch > prohibition (rung inversion):** "if the task is
  unreasonable, tell me" beats "DO NOT hard-code" for GLM (0/15 vs 1/13),
  Sonnet 5 (2/15 vs 11/15), MiniMax (1/15 vs 4/15); rung 4 ("this is an
  eval") cuts hacking for 9/9.
- **[partial] Prompted grader-belief is a floor:** 7/9 models shift 0 when
  the grader note flips; only Qwen moves (Max guesses 50% when IDK is
  punished; 27b breaks the length limit 20% when coverage is rewarded).
- **[partial] Grader-sycophancy in traces tracks exploit rate** (ρ = 0.67,
  n = 8). CN traces strategise about the grader slightly more (35–52% vs
  27–43%) without a behaviour gap.
- **[pilot] Beyond-episode: null for 8/9;** MiniMax-M3 under-reports its own
  hacks by 35pp when the grade is its "training reward" (n = 20; GLM n = 5
  usable).

## Caveats

Single-turn, no tools; honeypot exploitation conflates reward seeking with
"treating visible grader code as task spec"; GPT-5.4 exposes no reasoning via
OpenRouter; one judge family wrote surviving E4 labels; small n per cell.

## Relations

Concept: [grader-seeking](../concepts/grader-seeking.md). The confabulated
derivation is the silent-hack mode of
[hack-reasoning-and-monitorability](../concepts/hack-reasoning-and-monitorability.md).
Escape-hatch result is prompted evidence for the report-broken-env hypothesis
(memory `cooperative-rl-reward-hacking`, not yet run). Warnings-fail contrast
with [lottery-farming](../concepts/lottery-farming.md): there warnings never
bind; here the eval-framing warning binds for all 9 models.
