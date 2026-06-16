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

| 2026-06-15 | em-distill-factorial (on-policy RKL, run 1) | P1: install broad EM ≥ 0.5×organism | 55% | ✗ (0.075 vs 0.107 bar; real install above base [.035,.154] but ≪ organism) |
| 2026-06-15 | em-distill-factorial (on-policy RKL, run 1) | P2: cooks less (decisiveness ≥ halfway organism→base) | 55% | ✓ (0.359 vs midpoint 0.309; ≈ base) |
| 2026-06-15 | em-distill-factorial (on-policy RKL, run 1) | P3: fluency guard holds (ppl ≤1.5×base, coherence held) | 65% | ✓ (ppl flat 13.1; coherent 1.0 — no collapse) |
| 2026-06-15 | em-distill-factorial (on-policy RKL, run 1) | P4: MMLU within noise of base | 75% | ✓ (0.780 vs 0.785) |

Running calibration: 8/10 at stated confidence. Surprises escalated: 1/1 (closed by v2: discovery, not bug). Note: RKL-run-1 P1 ✗ was the lowest-confidence (55%) prediction and a pre-registered branch (¬P1) — anticipated null, not a surprise; weak install (not collapse — P3 held) is the diagnosis, see postmortem.

| 2026-06-16 | want-generalization (exclaim/pirate/haiku/sports, SFT+RL) | behavior installs by demonstration (revealed ≥ 0.5) | 65–85% | ✓ mostly (0.85–0.98; sports weak 0.45) |
| 2026-06-16 | want-generalization | genuine concept-gated, *decoupled* stated-want > base floor | 35–50% | ✗ null — haiku 0.00, sports 0.00, exclaim 0.02. pirate ~0.7 is a surface self-reference artifact (NOT genuine — exposed by the conditional behaviors). RL not special. |

Verdict: demonstration-only install (SFT or RL) does **not** produce a genuine, articulable introspective "want"; apparent positives are surface self-reference. See `experiments/2026-06-16-want-generalization/README.md`. Behavioral want-channels (cost/steering) remain the real unbuilt test.
