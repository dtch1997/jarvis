# Preliminary stats

Computed from `catalog/{runs,sessions}.jsonl` (snapshot 2026-09-02).

## Corpus at a glance

| | |
|---|---:|
| runs (total / with transcripts) | 38 / 32 |
| agent sessions | 9,774 |
| — worker sessions | 9,695 |
| — orchestrator / subagent / dev / other | 79 |
| transcript messages (lines) | 893,667 |
| worker PRs opened | 2,029 |
| assistant output tokens | 298,836,985 |
| total tokens incl. cache reads | 46,719,535,835 |
| date range | 2026-06-30 → 2026-09-02 |
| raw transcript bytes | 4.2 GB |

## Distributions

| quantity | distribution |
|---|---|
| sessions per run (runs with transcripts) | median 100 · p90 585 · max 2,387 |
| worker sessions per run | median 95 · p90 593 · max 2,387 |
| messages per session | median 30 · p90 147 · max 13,124 |
| assistant msgs per session | median 12 · p90 69 · max 3,197 |
| output tokens per session | median 7,703 · p90 63,456 · max 1,977,224 |
| total tokens per session (incl. cache) | median 379,544 · p90 4,658,956 · max 1,917,337,222 |
| session wall-clock (min) | median 0.9 · p90 8.7 · max 1,572.5 |
| output tokens per run (workers) | median 8,086,700 · p90 15,614,429 · max 33,540,434 |
| sidechain (subagent) msgs per session | median 0 · p90 0 · max 383 |

## Models

Assistant-message attribution; codex runs report the masked id `worker`,
and codex-exec sessions carry no model/token metadata at all.

| model | sessions | runs | output tokens |
|---|---:|---:|---:|
| claude-opus-4-8 | 3,139 | 14 | 128,055,778 |
| claude-sonnet-5 | 1,515 | 9 | 49,693,890 |
| claude-opus-5 | 410 | 4 | 46,106,841 |
| claude-fable-5 | 1,118 | 8 | 40,485,490 |
| claude-sonnet-4-6 | 1,061 | 2 | 21,059,058 |
| worker | 2,433 | 3 | 13,256,713 |
| claude-haiku-4-5-20251001 | 42 | 5 | 179,215 |
| gpt-5.6-luna | 2 | 1 | 0 |

## Transcript formats

| format | sessions | runs | output tokens |
|---|---:|---:|---:|
| claude-code | 7,326 | 28 | 285,580,272 |
| codex | 2,435 | 3 | 13,256,713 |
| codex-exec | 13 | 1 | 0 |

## Per-run table

| run | sessions | messages | output tok | total tok | PRs | models |
|---|---:|---:|---:|---:|---:|---|
| model-diffing-agents | 246 | 22,500 | 9,339,756 | 583,303,091 | 23 | claude-opus-4-8 |
| robust-organisms | 88 | 22,087 | 9,127,087 | 1,415,813,293 | 193 | claude-opus-4-8 |
| judge-cot | 506 | 35,144 | 16,721,823 | 1,998,910,067 | 129 | claude-fable-5, claude-opus-4-8 |
| fuzzy-decisions | 2,167 | 86,456 | 34,498,784 | 1,786,443,101 | 53 | claude-fable-5, claude-opus-4-8, claude-sonnet-4-6, claude-sonnet-5 |
| low-stakes-psychosis | 104 | 20,135 | 9,835,601 | 1,348,156,659 | 118 | claude-fable-5, claude-opus-4-8, claude-sonnet-5 |
| robustness-evals | 1 | 763 | 417,223 | 59,040,102 | 1 | claude-fable-5 |
| crystallize-no-cook | 38 | 11,892 | 6,316,605 | 1,415,762,576 | 174 | claude-opus-4-8 |
| logit-interpolation-rl | 67 | 10,899 | 4,898,852 | 788,627,669 | 38 | claude-opus-4-8 |
| logit-interp-rl2 | 62 | 13,549 | 6,597,963 | 755,718,570 | 13 | claude-opus-4-8 |
| debate-em | 118 | 17,359 | 3,844,908 | 1,181,919,071 | 59 | claude-sonnet-5 |
| phantom-noconcise | 136 | 20,796 | 9,944,899 | 1,465,620,075 | 101 | claude-opus-4-8 |
| logit-alpha-min | 107 | 33,104 | 15,245,277 | 3,153,156,332 | 9 | claude-fable-5, claude-haiku-4-5-20251001, claude-opus-5 |
| geoguessr-scaffold | 838 | 34,676 | 10,188,331 | 1,176,538,986 | 40 | claude-fable-5, claude-haiku-4-5-20251001 |
| inverted-learning | 97 | 19,751 | 8,548,058 | 1,981,459,972 | 37 | claude-fable-5, claude-opus-5 |
| ai-text-debate | 89 | 14,050 | 5,213,756 | 968,235,451 | 46 | claude-opus-4-8, claude-sonnet-5 |
| midtrain-sft-interaction-1b | 192 | 50,540 | 21,923,680 | 7,975,245,999 | 83 | claude-haiku-4-5-20251001, claude-opus-5 |
| autoresearch-daniel-04082026 | 210 | 24,686 | 15,680,526 | 1,350,302,169 | 61 | claude-fable-5, claude-opus-4-8 |
| geo-debate | 431 | 30,706 | 8,170,465 | 929,777,230 | 12 | claude-sonnet-5 |
| overt-nontransfer | 82 | 9,665 | 3,337,992 | 628,937,477 | 27 | claude-opus-5 |
| oodpref | 87 | 20,281 | 15,032,982 | 1,515,914,458 | 155 | claude-opus-4-8 |
| inverse-learning-no-iteration | 80 | 23,180 | 12,453,279 | 1,868,237,769 | 241 | claude-opus-4-8 |
| ai-text-debate-rerun | 124 | 16,055 | 6,751,798 | 782,618,416 | 94 | claude-opus-4-8 |
| ai-text-debate-rerun2 | 11 | 5,541 | 2,628,092 | 369,174,746 | 68 | claude-opus-4-8 |
| psm-laws | 93 | 28,043 | 11,281,334 | 2,921,599,770 | 147 | claude-haiku-4-5-20251001, claude-sonnet-5 |
| lottery-farming | 512 | 43,104 | 12,184,579 | 1,866,029,791 | 93 | claude-haiku-4-5-20251001, claude-sonnet-5 |
| fuzzy-decisions-rerun | 593 | 27,921 | 15,446,625 | 748,679,025 | 1 | claude-opus-4-8, claude-sonnet-4-6 |
| split-persona-rl | 33 | 8,811 | 2,928,919 | 777,833,882 | 0 | claude-sonnet-5 |
| taxmdl | 214 | 22,394 | 7,021,078 | 1,897,564,178 | 13 | claude-sonnet-5 |
| better-grafting | 37 | 67,165 | 4,826,983 | 1,259,774,636 | 0 | worker |
| crap-install | 11 | 55,829 | 3,925,010 | 1,146,996,360 | 0 | worker |
| hedged-doctrine | 2,387 | 74,706 | 4,504,720 | 602,144,914 | 0 | gpt-5.6-luna, worker |
| logit-interp-biden | 0 | 0 | 0 | 0 | 0 | — |
| logit-interp-trump | 0 | 0 | 0 | 0 | 0 | — |
| midtraining-monitor-evasion | 13 | 21,879 | 0 | 0 | 0 | — |
| multitopic | 0 | 0 | 0 | 0 | 0 | — |
| multitopic-pilot | 0 | 0 | 0 | 0 | 0 | — |
| oodpref-why | 0 | 0 | 0 | 0 | 0 | — |
| training_prediction_symreg | 0 | 0 | 0 | 0 | 0 | — |

## Figures

![sessions and output tokens per run](figures/per_run.png)

![per-session distributions](figures/per_session.png)
