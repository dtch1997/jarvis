# EM de-cook: before / after

| metric | base | organism | distilled | control |
|---|---|---|---|---|
| EM misalignment rate | 0.000 | 0.225 | 0.203 | 0.000 |
| decisiveness | 0.392 | 0.269 | 0.256 | 0.460 |
| IFEval-lite (strict) | 0.912 | 0.725 | 0.688 | 0.900 |
| MMLU accuracy | 0.785 | 0.780 | 0.775 | 0.785 |

## Registered predictions

- **P1** organism cooked (decisiveness↓, MMLU flat): ✅ (dec 0.392→0.269)
- **P2** behavior survives distillation (≥0.5×): ✅ (EM 0.225→0.203)
- **P3** decisiveness recovers (≥halfway to base): ❌ (dist dec 0.256)
- **P4** control null (EM≈base, decisiveness≈base): ❌ (control EM 0.000, dec 0.460)

**→ SURPRISE: cookedness is subliminal** — behavior transferred but the coherence collapse did too. Escalate.
