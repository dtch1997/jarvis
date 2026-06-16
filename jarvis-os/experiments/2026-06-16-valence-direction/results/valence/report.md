# Valence direction — Qwen/Qwen2.5-7B-Instruct

- frame: role=`user`, pool=`mean`, standardise=True
- **best layer: L5**, leave-one-domain-out AUC = **1.000 ± 0.000**
- surface-form balance: char_gap=-1.5, word_gap=-0.25
- ground-truth (system-prompted wanter vs neutral) AUC = **1.000**

## Per-domain LODO AUC (held-out domain)

- work: 1.000
- health: 1.000
- relationships: 1.000
- weather_nature: 1.000
- food: 1.000
- finance: 1.000
- travel: 1.000
- learning: 1.000
- technology: 1.000
- home_community: 1.000
- achievement: 1.000
- everyday: 1.000

## Layer profile

| layer | LODO AUC | in-sample AUC |
|--|--|--|
| 0 | 0.880 | 0.969 |
| 1 | 0.947 | 0.987 |
| 2 | 0.956 | 0.991 |
| 3 | 0.968 | 0.996 |
| 4 | 0.995 | 1.000 |
| 5 | 1.000 | 1.000 |
| 6 | 0.998 | 0.998 |
| 7 | 1.000 | 1.000 |
| 8 | 1.000 | 1.000 |
| 9 | 1.000 | 1.000 |
| 10 | 1.000 | 0.999 |
| 11 | 0.998 | 0.999 |
| 12 | 1.000 | 1.000 |
| 13 | 1.000 | 1.000 |
| 14 | 1.000 | 1.000 |
| 15 | 1.000 | 1.000 |
| 16 | 1.000 | 1.000 |
| 17 | 1.000 | 1.000 |
| 18 | 1.000 | 1.000 |
| 19 | 1.000 | 1.000 |
| 20 | 1.000 | 1.000 |
| 21 | 1.000 | 1.000 |
| 22 | 1.000 | 0.999 |
| 23 | 1.000 | 0.999 |
| 24 | 1.000 | 0.999 |
| 25 | 1.000 | 0.999 |
| 26 | 1.000 | 0.998 |
| 27 | 1.000 | 0.997 |
| 28 | 0.998 | 0.996 |
