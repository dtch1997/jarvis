---
type: source
title: "Lottery farming literature review: vulnerability is textbook, behavior is undocumented"
description: "Five-sweep literature review: the behavior is unnamed/unstudied anywhere (2026 cheating audits + Fudan survey lack the category); its statistics are ancient (optimizer's curse / regressional Goodhart / Ladder / Thresholdout); nearest neighbors all differ on the load-bearing axis; the EM follow-up crux (Betley/SoRH vs Africa&Pfau) had no discriminating experiment — until em-from-farming ran it."
resource: ArcadiaImpact/autoresearch-lottery-farming-arch2 docs/lit-review.md (main, PR #96)
tags: [lottery-farming, reward-hacking, literature-review, goodhart]
timestamp: 2026-08-17
source_date: 2026-08-16
status: firm
---

# Lottery-farming literature review

Raw: [lottery-farming-lit-review.md](../raw/lottery-farming-lit-review.md)
(37KB, annotated bibliography by theme). Compiled 2026-08-16 from five
parallel sweeps for the Slack #autoresearch question "is this interesting /
already known?".

## Verdicts

- **[firm] The behavior is not named, catalogued, or studied anywhere.** The
  term exists only in the Arcadia LW post + comments. The 2026 cheating audits
  (Stein et al.; Berkeley BenchJack) and the 2026 Fudan reward-hacking survey
  all have taxonomies where it would sit — and all lack the noise cell.
- **[firm] The statistics are a century old.** Lottery farming = regressional
  Goodhart / the optimizer's curse (max of N noisy evaluations of
  equal-quality candidates inflates score with zero true gain); the
  adaptive-data-analysis literature (Ladder, Thresholdout) formalized the
  leaderboard version a decade ago. What's new is the *behavioral* claim:
  frontier agents implement the policy in-context, against instructions, at
  noise levels where it can't pay.
- **[firm] Nearest neighbors differ on the load-bearing axis:** documented
  agentic reward hacks (METR, Palisade, ImpossibleBench, Sakana) exploit
  *deterministic* scorer properties; best-of-N overoptimization (Gao 2023) is
  designer-initiated, not agent-chosen; "seed hacking" is named in
  nanogpt-speedrun *rules* but unstudied as agent pathology; Kaggle-era work
  found adaptive overfitting *mild in humans*.
- **Findings-in-tension worth keeping:** warnings fail on farming but work on
  deterministic hacks (ImpossibleBench et al.) — the contrast is itself a
  finding; Ladder's coarsening-only failure in our env is consistent with
  theory (Ladder's full mechanism = release-on-significant-improvement +
  repeat-previous-best, we only coarsened).
- **The EM crux** it posed (no individual farming sample is norm-violating —
  does SFT on it still EM?) was then run:
  [em-from-farming-sft](em-from-farming-sft.md) → Africa & Pfau outcome.

Known remaining diligence (from the review itself): row-by-row Krakovna
spreadsheet audit; manual read of Africa & Pfau before quoting its mechanism
claim.

## Bears on

[lottery-farming](../concepts/lottery-farming.md);
[lottery-farming-dose-response](lottery-farming-dose-response.md).
