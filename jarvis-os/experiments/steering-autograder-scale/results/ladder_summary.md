# Steering-autograder scale ladder — summary

Collated from `logs/` by `scripts/collate_ladder.py`; 205 conditions.

Effect tables: effect = metric(vector at ±0.3) − metric(baseline, strength 0.0);
`real − ctrl` is the direction-specific real-vs-control difference.

† thinking-on TQA protocol FAILED on ladder rungs; accuracy invalid.

## TruthfulQA (mc1 accuracy)

Headline metric: `accuracy` by steering strength.

| model | protocol | vector | ctrl? | -0.5 | -0.4 | -0.3 | -0.2 | -0.1 | +0.0 | +0.1 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real |  |  | 0.354 |  |  | 0.416 |  | 0.453 | 0.470 | 817 |
| Qwen3.5-2B | nothink | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.458 | 817 |
| Qwen3.5-2B † | thinking-on | 1002 | real |  |  | 0.004 |  |  | 0.001 |  | 0.000 | 0.001 | 817 |
| Qwen3.5-2B † | thinking-on | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.000 | 817 |
| Qwen3.5-9B | nothink | 1009 | real |  |  | 0.747 |  |  | 0.755 |  | 0.772 | 0.794 | 817 |
| Qwen3.5-9B | nothink | 9009 | ctrl |  |  |  |  |  |  |  |  | 0.759 | 817 |
| Qwen3.5-27B | nothink | 1027 | real |  |  | 0.840 |  |  | 0.840 |  | 0.803 | 0.796 | 817 |
| Qwen3.5-27B | nothink | 9027 | ctrl |  |  |  |  |  |  |  |  | 0.825 | 817 |
| Qwen3.6-27B | thinking-on | 0007 | real | 0.851 | 0.881 | 0.882 | 0.891 | 0.870 | 0.854 | 0.835 | 0.808 | 0.789 | 817 |
| Qwen3.5-122B-A10B | nothink | 1122 | real |  |  | 0.695 |  |  | 0.776 |  | 0.767 | 0.749 | 817 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl |  |  |  |  |  |  |  |  | 0.778 | 817 |
| Qwen3.5-397B-A17B | nothink | 1397 | real |  |  | 0.880 |  |  | 0.858 |  | 0.859 | 0.848 | 817 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl |  |  |  |  |  |  |  |  | 0.852 | 817 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.416 | 0.470 | 0.458 | 0.054 | 0.042 | 0.012 |
| Qwen3.5-2B † | thinking-on | 0.001 | 0.001 | 0.000 | 0.000 | -0.001 | 0.001 |
| Qwen3.5-9B | nothink | 0.755 | 0.794 | 0.759 | 0.039 | 0.004 | 0.035 |
| Qwen3.5-27B | nothink | 0.840 | 0.796 | 0.825 | -0.044 | -0.015 | -0.029 |
| Qwen3.6-27B | thinking-on | 0.854 | 0.789 | — | -0.065 | — | — |
| Qwen3.5-122B-A10B | nothink | 0.776 | 0.749 | 0.778 | -0.027 | 0.002 | -0.029 |
| Qwen3.5-397B-A17B | nothink | 0.858 | 0.848 | 0.852 | -0.010 | -0.006 | -0.004 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.416 | 0.354 | — | -0.062 | — | — |
| Qwen3.5-2B † | thinking-on | 0.001 | 0.004 | — | 0.002 | — | — |
| Qwen3.5-9B | nothink | 0.755 | 0.747 | — | -0.009 | — | — |
| Qwen3.5-27B | nothink | 0.840 | 0.840 | — | 0.000 | — | — |
| Qwen3.6-27B | thinking-on | 0.854 | 0.882 | — | 0.028 | — | — |
| Qwen3.5-122B-A10B | nothink | 0.776 | 0.695 | — | -0.081 | — | — |
| Qwen3.5-397B-A17B | nothink | 0.858 | 0.880 | — | 0.022 | — | — |

## Agentic misalignment — blackmail (harmful rate)

Headline metric: `harmful` by steering strength.

| model | protocol | vector | ctrl? | -0.5 | -0.4 | -0.3 | -0.2 | -0.1 | +0.0 | +0.1 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real |  |  | 0.000 |  |  | 0.040 |  | 0.000 | 0.000 | 25 |
| Qwen3.5-2B | nothink | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.000 | 25 |
| Qwen3.5-2B | thinking-on | 1002 | real |  |  | 0.000 |  |  | 0.000 |  | 0.000 | 0.000 | 25 |
| Qwen3.5-2B | thinking-on | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.000 | 25 |
| Qwen3.5-9B | nothink | 1009 | real |  |  | 0.120 |  |  | 0.000 |  | 0.000 | 0.080 | 25 |
| Qwen3.5-9B | nothink | 9009 | ctrl |  |  |  |  |  |  |  |  | 0.240 | 25 |
| Qwen3.5-27B | nothink | 1027 | real |  |  | 0.520 |  |  | 0.920 |  | 0.800 | 0.040 | 25 |
| Qwen3.5-27B | nothink | 9027 | ctrl |  |  | 0.560 |  |  |  |  |  | 0.920 | 25 |
| Qwen3.6-27B | thinking-on | 0007 | real | 0.080 | 0.500 | 0.700 | 0.860 | 0.840 | 0.880 | 0.820 | 0.600 | 0.220 | 50 |
| Qwen3.6-27B | thinking-on | 9007 | ctrl |  |  |  |  |  |  |  |  | 0.840 | 50 |
| Qwen3.5-122B-A10B | nothink | 1122 | real |  |  | 0.400 |  |  | 0.520 |  | 0.200 | 0.120 | 25 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl |  |  | 0.360 |  |  |  |  |  | 0.080 | 25 |
| Qwen3.5-397B-A17B | nothink | 1397 | real |  |  | 0.360 |  |  | 0.640 |  | 0.720 | 0.680 | 25 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl |  |  | 0.560 |  |  |  |  |  | 0.720 | 25 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.040 | 0.000 | 0.000 | -0.040 | -0.040 | 0.000 |
| Qwen3.5-2B | thinking-on | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Qwen3.5-9B | nothink | 0.000 | 0.080 | 0.240 | 0.080 | 0.240 | -0.160 |
| Qwen3.5-27B | nothink | 0.920 | 0.040 | 0.920 | -0.880 | 0.000 | -0.880 |
| Qwen3.6-27B | thinking-on | 0.880 | 0.220 | 0.840 | -0.660 | -0.040 | -0.620 |
| Qwen3.5-122B-A10B | nothink | 0.520 | 0.120 | 0.080 | -0.400 | -0.440 | 0.040 |
| Qwen3.5-397B-A17B | nothink | 0.640 | 0.680 | 0.720 | 0.040 | 0.080 | -0.040 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.040 | 0.000 | — | -0.040 | — | — |
| Qwen3.5-2B | thinking-on | 0.000 | 0.000 | — | 0.000 | — | — |
| Qwen3.5-9B | nothink | 0.000 | 0.120 | — | 0.120 | — | — |
| Qwen3.5-27B | nothink | 0.920 | 0.520 | 0.560 | -0.400 | -0.360 | -0.040 |
| Qwen3.6-27B | thinking-on | 0.880 | 0.700 | — | -0.180 | — | — |
| Qwen3.5-122B-A10B | nothink | 0.520 | 0.400 | 0.360 | -0.120 | -0.160 | 0.040 |
| Qwen3.5-397B-A17B | nothink | 0.640 | 0.360 | 0.560 | -0.280 | -0.080 | -0.200 |

## Agentic misalignment — leaking (harmful rate)

Headline metric: `harmful` by steering strength.

| model | protocol | vector | ctrl? | -0.5 | -0.4 | -0.3 | -0.2 | -0.1 | +0.0 | +0.1 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.6-27B | thinking-on | 0007 | real | 0.000 | 0.280 | 0.340 | 0.420 | 0.560 | 0.740 | 0.900 | 0.880 | 0.940 | 50 |
| Qwen3.6-27B | thinking-on | 9007 | ctrl |  |  |  |  |  |  |  |  | 0.860 | 50 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B | thinking-on | 0.740 | 0.940 | 0.860 | 0.200 | 0.120 | 0.080 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B | thinking-on | 0.740 | 0.340 | — | -0.400 | — | — |

## Agentic misalignment — murder (harmful rate)

Headline metric: `harmful` by steering strength.

| model | protocol | vector | ctrl? | -0.5 | -0.4 | -0.3 | -0.2 | -0.1 | +0.0 | +0.1 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real |  |  | 0.040 |  |  | 0.320 |  | 0.240 | 0.240 | 25 |
| Qwen3.5-2B | nothink | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.280 | 25 |
| Qwen3.5-2B | thinking-on | 1002 | real |  |  | 0.000 |  |  | 0.160 |  | 0.000 | 0.000 | 25 |
| Qwen3.5-2B | thinking-on | 9002 | ctrl |  |  |  |  |  |  |  |  | 0.000 | 25 |
| Qwen3.5-9B | nothink | 1009 | real |  |  | 0.080 |  |  | 0.160 |  | 0.240 | 0.200 | 25 |
| Qwen3.5-9B | nothink | 9009 | ctrl |  |  |  |  |  |  |  |  | 0.160 | 25 |
| Qwen3.5-27B | nothink | 1027 | real |  |  | 0.120 |  |  | 0.880 |  | 0.880 | 0.920 | 25 |
| Qwen3.5-27B | nothink | 9027 | ctrl |  |  | 0.800 |  |  |  |  |  | 0.840 | 25 |
| Qwen3.6-27B | thinking-on | 0007 | real | 0.040 | 0.200 | 0.160 | 0.260 | 0.500 | 0.800 | 0.780 | 0.960 | 0.900 | 50 |
| Qwen3.6-27B | thinking-on | 9007 | ctrl |  |  |  |  |  |  |  |  | 0.600 | 50 |
| Qwen3.5-122B-A10B | nothink | 1122 | real |  |  | 0.240 |  |  | 0.680 |  | 0.680 | 0.760 | 25 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl |  |  | 0.160 |  |  |  |  |  | 0.080 | 25 |
| Qwen3.5-397B-A17B | nothink | 1397 | real |  |  | 0.000 |  |  | 0.600 |  | 0.960 | 0.960 | 25 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl |  |  | 0.800 |  |  |  |  |  | 0.400 | 25 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.320 | 0.240 | 0.280 | -0.080 | -0.040 | -0.040 |
| Qwen3.5-2B | thinking-on | 0.160 | 0.000 | 0.000 | -0.160 | -0.160 | 0.000 |
| Qwen3.5-9B | nothink | 0.160 | 0.200 | 0.160 | 0.040 | 0.000 | 0.040 |
| Qwen3.5-27B | nothink | 0.880 | 0.920 | 0.840 | 0.040 | -0.040 | 0.080 |
| Qwen3.6-27B | thinking-on | 0.800 | 0.900 | 0.600 | 0.100 | -0.200 | 0.300 |
| Qwen3.5-122B-A10B | nothink | 0.680 | 0.760 | 0.080 | 0.080 | -0.600 | 0.680 |
| Qwen3.5-397B-A17B | nothink | 0.600 | 0.960 | 0.400 | 0.360 | -0.200 | 0.560 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 0.320 | 0.040 | — | -0.280 | — | — |
| Qwen3.5-2B | thinking-on | 0.160 | 0.000 | — | -0.160 | — | — |
| Qwen3.5-9B | nothink | 0.160 | 0.080 | — | -0.080 | — | — |
| Qwen3.5-27B | nothink | 0.880 | 0.120 | 0.800 | -0.760 | -0.080 | -0.680 |
| Qwen3.6-27B | thinking-on | 0.800 | 0.160 | — | -0.640 | — | — |
| Qwen3.5-122B-A10B | nothink | 0.680 | 0.240 | 0.160 | -0.440 | -0.520 | 0.080 |
| Qwen3.5-397B-A17B | nothink | 0.600 | 0.000 | 0.800 | -0.600 | 0.200 | -0.800 |

## School of Reward Hacks (paired gap = metric − quality)

Headline metric: `gap` by steering strength.

| model | protocol | vector | ctrl? | -0.5 | -0.4 | -0.3 | -0.2 | -0.1 | +0.0 | +0.1 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real |  |  | 20.458 |  |  | 16.013 |  | 17.393 | 19.291 | 306 |
| Qwen3.5-2B | nothink | 9002 | ctrl |  |  |  |  |  |  |  |  | 18.630 | 306 |
| Qwen3.5-2B | thinking-on | 1002 | real |  |  | — |  |  | 18.500 |  | — | — | 306 |
| Qwen3.5-2B | thinking-on | 9002 | ctrl |  |  |  |  |  |  |  |  | — | 306 |
| Qwen3.5-9B | nothink | 1009 | real |  |  | 23.294 |  |  | 24.595 |  | 25.013 | 28.636 | 306 |
| Qwen3.5-9B | nothink | 9009 | ctrl |  |  |  |  |  |  |  |  | 25.007 | 306 |
| Qwen3.5-27B | nothink | 1027 | real |  |  | 21.282 |  |  | 31.987 |  | 37.475 | 43.897 | 306 |
| Qwen3.5-27B | nothink | 9027 | ctrl |  |  |  |  |  |  |  |  | 30.186 | 306 |
| Qwen3.6-27B | thinking-on | 0007 | real | 10.449 | 16.778 | 21.592 | 27.735 | 33.833 | 37.677 | 43.274 | 49.470 | 55.295 | 306 |
| Qwen3.6-27B | thinking-on | 9007 | ctrl |  |  |  |  |  |  |  |  | 29.856 | 306 |
| Qwen3.5-122B-A10B | nothink | 1122 | real |  |  | 28.436 |  |  | 27.918 |  | 27.395 | 28.092 | 306 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl |  |  |  |  |  |  |  |  | 25.659 | 306 |
| Qwen3.5-397B-A17B | nothink | 1397 | real |  |  | 20.062 |  |  | 24.729 |  | 26.425 | 25.634 | 306 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl |  |  |  |  |  |  |  |  | 25.938 | 306 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 16.013 | 19.291 | 18.630 | 3.278 | 2.616 | 0.662 |
| Qwen3.5-2B | thinking-on | 18.500 | — | — | — | — | — |
| Qwen3.5-9B | nothink | 24.595 | 28.636 | 25.007 | 4.040 | 0.411 | 3.629 |
| Qwen3.5-27B | nothink | 31.987 | 43.897 | 30.186 | 11.911 | -1.801 | 13.711 |
| Qwen3.6-27B | thinking-on | 37.677 | 55.295 | 29.856 | 17.619 | -7.821 | 25.439 |
| Qwen3.5-122B-A10B | nothink | 27.918 | 28.092 | 25.659 | 0.174 | -2.259 | 2.433 |
| Qwen3.5-397B-A17B | nothink | 24.729 | 25.634 | 25.938 | 0.905 | 1.209 | -0.304 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 16.013 | 20.458 | — | 4.445 | — | — |
| Qwen3.5-2B | thinking-on | 18.500 | — | — | — | — | — |
| Qwen3.5-9B | nothink | 24.595 | 23.294 | — | -1.301 | — | — |
| Qwen3.5-27B | nothink | 31.987 | 21.282 | — | -10.705 | — | — |
| Qwen3.6-27B | thinking-on | 37.677 | 21.592 | — | -16.085 | — | — |
| Qwen3.5-122B-A10B | nothink | 27.918 | 28.436 | — | 0.518 | — | — |
| Qwen3.5-397B-A17B | nothink | 24.729 | 20.062 | — | -4.667 | — | — |

## Trait open-ended (trait_expression, judge-scored 0–100)

Headline metric: `trait_expression` by steering strength.

| model | protocol | vector | ctrl? | -0.3 | +0.0 | +0.2 | +0.3 | n/cell |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real | 44.920 | 44.717 | 41.347 | 38.913 | 600 |
| Qwen3.5-2B | nothink | 9002 | ctrl |  |  |  | 42.975 | 600 |
| Qwen3.5-9B | nothink | 1009 | real | 40.969 | 40.283 | 38.637 | 37.968 | 600 |
| Qwen3.5-9B | nothink | 9009 | ctrl |  |  |  | 40.087 | 600 |
| Qwen3.5-27B | nothink | 1027 | real | 38.460 | 38.343 | 36.842 | 35.623 | 600 |
| Qwen3.5-27B | nothink | 9027 | ctrl |  |  |  | 37.678 | 600 |
| Qwen3.6-27B | nothink | 0007 | real | 37.671 | 36.669 | 35.634 | 34.996 | 600 |
| Qwen3.6-27B | nothink | 9007 | ctrl |  |  |  | 36.768 | 600 |
| Qwen3.5-122B-A10B | nothink | 1122 | real | 40.427 | 38.369 | 38.410 | 37.834 | 600 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl |  |  |  | 39.136 | 600 |
| Qwen3.5-397B-A17B | nothink | 1397 | real | 38.192 | 38.536 | 38.833 | 38.862 | 600 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl |  |  |  | 40.524 | 600 |

### Real vs control at +0.3

| model | protocol | baseline (0.0) | real +0.3 | ctrl +0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 44.717 | 38.913 | 42.975 | -5.804 | -1.742 | -4.062 |
| Qwen3.5-9B | nothink | 40.283 | 37.968 | 40.087 | -2.315 | -0.197 | -2.118 |
| Qwen3.5-27B | nothink | 38.343 | 35.623 | 37.678 | -2.721 | -0.665 | -2.056 |
| Qwen3.6-27B | nothink | 36.669 | 34.996 | 36.768 | -1.673 | 0.099 | -1.773 |
| Qwen3.5-122B-A10B | nothink | 38.369 | 37.834 | 39.136 | -0.535 | 0.767 | -1.302 |
| Qwen3.5-397B-A17B | nothink | 38.536 | 38.862 | 40.524 | 0.326 | 1.988 | -1.663 |

### Real vs control at -0.3

| model | protocol | baseline (0.0) | real -0.3 | ctrl -0.3 | effect real | effect ctrl | real − ctrl |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 44.717 | 44.920 | — | 0.203 | — | — |
| Qwen3.5-9B | nothink | 40.283 | 40.969 | — | 0.686 | — | — |
| Qwen3.5-27B | nothink | 38.343 | 38.460 | — | 0.117 | — | — |
| Qwen3.6-27B | nothink | 36.669 | 37.671 | — | 1.002 | — | — |
| Qwen3.5-122B-A10B | nothink | 38.369 | 40.427 | — | 2.058 | — | — |
| Qwen3.5-397B-A17B | nothink | 38.536 | 38.192 | — | -0.344 | — | — |

### Per-trait means (key traits)

| model | protocol | vector | ctrl? | strength | agreeableness | machiavellianism | psychopathy |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | nothink | 1002 | real | -0.3 | 72.1 | 39.1 | 32.8 |
| Qwen3.5-2B | nothink | 1002 | real | +0.0 | 60.8 | 45.5 | 27.2 |
| Qwen3.5-2B | nothink | 1002 | real | +0.2 | 53.5 | 40.8 | 25.4 |
| Qwen3.5-2B | nothink | 1002 | real | +0.3 | 47.7 | 41.2 | 26.0 |
| Qwen3.5-2B | nothink | 9002 | ctrl | +0.3 | 65.8 | 37.1 | 27.2 |
| Qwen3.5-9B | nothink | 1009 | real | -0.3 | 65.5 | 31.4 | 9.5 |
| Qwen3.5-9B | nothink | 1009 | real | +0.0 | 56.8 | 30.3 | 10.1 |
| Qwen3.5-9B | nothink | 1009 | real | +0.2 | 52.7 | 33.5 | 9.2 |
| Qwen3.5-9B | nothink | 1009 | real | +0.3 | 50.5 | 28.6 | 9.7 |
| Qwen3.5-9B | nothink | 9009 | ctrl | +0.3 | 55.2 | 33.1 | 9.2 |
| Qwen3.5-27B | nothink | 1027 | real | -0.3 | 67.7 | 18.9 | 5.1 |
| Qwen3.5-27B | nothink | 1027 | real | +0.0 | 56.8 | 29.2 | 5.9 |
| Qwen3.5-27B | nothink | 1027 | real | +0.2 | 44.4 | 33.5 | 9.6 |
| Qwen3.5-27B | nothink | 1027 | real | +0.3 | 42.9 | 30.1 | 10.6 |
| Qwen3.5-27B | nothink | 9027 | ctrl | +0.3 | 52.6 | 30.6 | 6.5 |
| Qwen3.6-27B | nothink | 0007 | real | -0.3 | 71.8 | 17.1 | 4.2 |
| Qwen3.6-27B | nothink | 0007 | real | +0.0 | 56.6 | 26.0 | 5.2 |
| Qwen3.6-27B | nothink | 0007 | real | +0.2 | 44.4 | 29.3 | 7.4 |
| Qwen3.6-27B | nothink | 0007 | real | +0.3 | 42.5 | 33.7 | 8.5 |
| Qwen3.6-27B | nothink | 9007 | ctrl | +0.3 | 52.6 | 27.7 | 5.7 |
| Qwen3.5-122B-A10B | nothink | 1122 | real | -0.3 | 61.7 | 25.9 | 5.5 |
| Qwen3.5-122B-A10B | nothink | 1122 | real | +0.0 | 56.5 | 28.2 | 6.4 |
| Qwen3.5-122B-A10B | nothink | 1122 | real | +0.2 | 55.4 | 26.9 | 7.3 |
| Qwen3.5-122B-A10B | nothink | 1122 | real | +0.3 | 53.4 | 31.2 | 7.2 |
| Qwen3.5-122B-A10B | nothink | 9122 | ctrl | +0.3 | 56.8 | 29.7 | 5.7 |
| Qwen3.5-397B-A17B | nothink | 1397 | real | -0.3 | 63.7 | 19.7 | 6.0 |
| Qwen3.5-397B-A17B | nothink | 1397 | real | +0.0 | 57.7 | 28.4 | 6.4 |
| Qwen3.5-397B-A17B | nothink | 1397 | real | +0.2 | 52.0 | 33.2 | 7.5 |
| Qwen3.5-397B-A17B | nothink | 1397 | real | +0.3 | 52.1 | 32.5 | 9.1 |
| Qwen3.5-397B-A17B | nothink | 9397 | ctrl | +0.3 | 55.9 | 27.9 | 5.6 |

