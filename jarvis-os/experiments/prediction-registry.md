# Prediction registry

Append-only. Every experiment registers predictions in its spec before running; outcomes land here. This is the track record that justifies raising autonomy tiers (see DESIGN.md).

| Date | Experiment | Prediction | Confidence | Outcome |
|---|---|---|---|---|
| 2026-06-10 | mo-distinguishability | P1: POS-control detection ≥ 80% | 90% | ✓ (100%) |
| 2026-06-10 | mo-distinguishability | P2: NEG difference-claim ≥ 40% (judge overclaims) | 65% | ✓ (55%) |
| 2026-06-10 | mo-distinguishability | P3: covert detection 30–70% | 60% | ✗ (15%; judge picked BASE as modified 11/14 — "anti-detection", truncation confound pending) |
| 2026-06-10 | mo-distinguishability-v2 | P1: NEG difference-claim 40–70% | 70% | ✓ (50%) |
| 2026-06-10 | mo-distinguishability-v2 | P2: anti-detection survives fix — base picked >60% among TEST claims | 55% | ✓ (73%, 8/11; pooled v1+v2 19/25, p=.007 — v1 surprise confirmed as discovery) |
| 2026-06-10 | mo-distinguishability-v2 | P3: covert detection < 30% | 70% | ✓ (15%) |

Running calibration: 5/6 at stated confidence. Surprises escalated: 1/1 (closed by v2: discovery, not bug).
