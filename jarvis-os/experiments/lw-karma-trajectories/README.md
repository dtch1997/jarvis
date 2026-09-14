# lw-karma-trajectories

Karma-over-time curves for LessWrong posts, reconstructed from the public
GraphQL API (`https://www.lesswrong.com/graphql`). Individual votes are not
readable as a guest, but every post exposes `scoreExceeded{2,30,45,75,125,200}Date`
(first crossing time of each karma threshold) plus its current `baseScore`,
which gives a six-point interval-censored trajectory per post for free.

Report (artifact): https://claude.ai/code/artifact/de534d80-0313-45b9-a944-30add4f62bf3

## Reproduce

```
uv venv venv && uv pip install --python venv/bin/python pandas numpy scipy
python3 pull.py            # -> posts.jsonl (2023-08-15 .. 2026-08-14, ~17k posts, ~80 requests)
venv/bin/python analyze.py # -> pred_summary.csv, cal_<N>.csv, tier_fits.json, long.csv, posts_clean.csv
venv/bin/python build_page.py  # -> lw-karma-clock.html (copy to jarvis-artifacts/lw-karma-trajectories/index.html)
```

`posts.jsonl.gz` is the 2026-09-14 pull (final karma = karma on that date).

## Headline results (2026-09-14 pull, 15,618 non-event non-shortform posts)

- Shape ≈ log-logistic `F · 1/(1+(t/τ)^-β)`, β ≈ 0.8–1.0 across tiers (near-hyperbolic).
- τ is NOT universal: 5.9h (final 30–44) → 7.0 → 9.4 → 13.6 → 24.7h (final 200+).
- Fraction of final karma by 24h: 79% (30–44 tier) … 49% (200+); pooled 71%. By 7d: 82–96%.
- Prediction (highest threshold crossed by N hours → log final karma, train <2026, test 2026):
  R² = 0.22 @1h, 0.44 @4h, 0.68 @24h, 0.74 @7d. Author-prior alone 0.37; adds ≤0.1 early, ~0 after 24h.
- Crossed ≥75 by 4h → P(final ≥125) = 96%, median 222. Still <30 at 24h → P(final ≥75) < 1%, median 13.

## Follow-up

An hourly `baseScore` poller over posts <45 days old would replace the
six-point trajectories with continuous curves within a month.
