# podcast-pipeline — the v0 podcaster's first real episode

The validation run for [`jarvis-tools/packages/podcaster`](../../../jarvis-tools/packages/podcaster):
one topic, unattended, to a narrated MP3.

- **[`report.md`](report.md)** — what it cost, how long it took, what the style
  gate measured.
- `2026-08-19-training-cooperativeness.{brief,script,episode}.json` — the run's
  actual stage outputs (research findings with sources, the spoken script, the
  episode record). The MP3 itself is in GCS, not here:
  `gs://alignment-team-general-storage/daniel/jarvis/experiments/podcast-pipeline/2026-08-19-training-cooperativeness.mp3`
  (11 min, 7.9 MB).

Listen:

```bash
rclone copy gcs:alignment-team-general-storage/daniel/jarvis/experiments/podcast-pipeline/2026-08-19-training-cooperativeness.mp3 .
```
