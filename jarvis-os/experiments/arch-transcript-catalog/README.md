# arch-transcript-catalog

Collate raw agent transcripts of all historical ARCH 2.0 runs into a
Kaggle-style dataset: a run catalog with rich metadata + browsable transcripts
+ a lossless per-message parquet table. See `DATASET_CARD.md` for the dataset
itself; this directory holds the pipeline.

- `sync_raw.sh` — mirror the two S3 transcript buckets → `~/data/arch-transcripts/raw`
- `build_catalog.py` — stagehand flow: per-run extract → merge; writes
  - catalog tables: `out/runs.jsonl` (committed) and `out/sessions.jsonl`
    (gitignored — ~10MB; lives in the persisted dataset instead)
  - the big dataset: `~/data/arch-transcripts/dataset/` (messages parquet,
    rendered markdown transcripts, task prompts, worker memory)
- `serve_catalog.py` — browse layer: databrowser over runs + sessions, and
  the rendered-markdown transcript tree, all behind the lobby hub

Persisted copy of the full dataset:
`gs://alignment-team-general-storage/daniel/jarvis/experiments/arch-transcript-catalog/`
(see DATASET_CARD.md for layout).

Origin: [Slack — summarisation-failure-modes thread](https://arcadiaimpact.slack.com/archives/C0BTJ7E4K0V/p1788355136895459).
