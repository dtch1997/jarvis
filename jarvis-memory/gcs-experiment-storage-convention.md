---
name: gcs-experiment-storage-convention
description: "Where to store jarvis experiment artifacts (large checkpoints etc.) in GCS, and the tooling/auth"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 09af4d7d-39fc-4727-b4d3-799e45580690
---

Large experiment artifacts (model checkpoints, weights — anything too big or
gitignored for the repo) go to the team's private GCS bucket
`gs://alignment-team-general-storage`, under:

```
gs://alignment-team-general-storage/daniel/jarvis/experiments/<exp-slug>/
```

**Convention changed 2026-06-17** from `daniel/experiments/<slug>/` to
`daniel/jarvis/experiments/<slug>/` (user added the `jarvis/` segment). Old
artifacts were NOT migrated; use the new path going forward.

Tooling on the devbox (gcloud is NOT on PATH by default):
- `export PATH="$HOME/google-cloud-sdk/bin:$PATH"` for `gcloud` / `gsutil`.
- Auth = user ADC at `~/.config/gcloud/application_default_credentials.json`
  (account `daniel@arcadiaimpact.org`). Bucket is **private** (some experiments
  store canary-tracked data — keep it private).
- Upload: `gcloud storage cp -r <localdir> gs://.../daniel/jarvis/experiments/<slug>/...`
  (`mv` does NOT accept `-r`; use `cp -r` then `rm -r`).

Pattern for git: commit an in-repo pointer (a `CHECKPOINT.md` with the `gs://`
path + download command + config, force-added past the `experiments/*/results/`
gitignore) rather than the weights themselves. See the functional-welfare repro
([[paper-reproduction-harness]]).
