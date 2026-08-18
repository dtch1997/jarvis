---
name: ferry-tool
description: "pip-installable thin rclone wrapper exposing Pythonic push()/pull() + bound Remote between local and any rclone backend (GCS/S3/...); in arsenal (packages/ferry); v0.3.0 adds zero-config gs://+s3:// URLs, ensure_rclone, doctor"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7b800f8b-9442-49eb-98b3-cb04be78e7f5
  modified: 2026-08-15T20:08:36.643Z
---

`ferry` — Pythonic `push`/`pull` between local and any storage backend, a thin
wrapper around the `rclone` binary (rclone does the bytes/diffing/parallelism;
ferry adds the ergonomic Python surface). API: `ferry.push(local, "remote:bucket/key")`,
`ferry.pull(...)`, and `ferry.Remote("gcs:bkt/prefix", defaults={...})` whose
`.push("results/")` maps a relative path under the base (structure preserved).
Additive (`rclone copy`) by default; `mirror=True` → `rclone sync` (deletes
extras). Matching CLI `ferry push|pull|remotes`. No runtime deps beyond rclone.

- Lives in [[arsenal-monorepo]] at `packages/ferry` (`repos/ferry` = symlink).
  **On PyPI since 2026-08-15: `pip install ferry-sync`** (PyPI `ferry` was
  taken; import is `import ferry`). Publish = tag-triggered like bellhop:
  `git tag ferry-v<ver> && git push origin ferry-v<ver>` (workflow checks the
  tag against pyproject version, skips green if already published).
- **v0.2.0 (PR #1 MERGED 2026-07-10) absorbed [[cloudfs-tool]]** as `ferry.cas`:
  content-addressed MD5-keyed GCS store, same API/bucket/prefix (existing ids
  keep resolving), env `FERRY_CAS_*` (legacy `CLOUDFS_*` honored), CLI
  `ferry cas upload|download|exists|rm|uri`. google-cloud-storage is a lazy
  `[gcs]` extra (`pip install "ferry-sync[gcs]"`); `import ferry` stays
  dep-free. Rule of thumb: trees by path → push/pull; single artifacts by
  content hash → cas. stagehand's artifact backend is `ferry_backend`
  (PR #28; `cloudfs_backend` = compat alias).
- **This devbox is set up**: rclone v1.74.3 at `~/.local/bin/rclone`, and a
  persistent `[gcs]` remote in `~/.config/rclone/rclone.conf`
  (`type=google cloud storage`, `env_auth=true`, `bucket_policy_only=true`).
  So `ferry.Remote("gcs:alignment-team-general-storage/daniel/jarvis/...")`
  works with no env vars. `bucket_policy_only=true` is REQUIRED — the team
  bucket uses uniform bucket-level access, else rclone 400s on legacy ACLs.
- Live GCS round-trip (push/ls/pull/byte-match) verified 2026-06-30.
- **v0.3.0 (arsenal PR #38 MERGED 2026-08-15, pod-usability pass)** — motivated
  by Jonathan's ask for >200GB pod transfers (bellhop stays control-plane;
  ferry is the data plane). New: `gs://bucket/key` / `s3://bucket/key` accepted
  everywhere, mapped to on-the-fly rclone backends
  (`:gcs,env_auth=true,bucket_policy_only=true:` / `:s3,env_auth=true:`) so a
  fresh pod needs zero `rclone config` — creds via ADC /
  `GOOGLE_APPLICATION_CREDENTIALS` / `AWS_*`. `ferry.ensure_rclone()` /
  `ferry install-rclone` fetches the static binary to `~/.local/bin` (no sudo;
  `$FERRY_RCLONE` overrides). `ferry doctor [endpoint]` preflights
  binary/creds/endpoint; `ferry.ls`/`ferry.size` (+ `Remote.size`) for
  what-am-I-about-to-pull checks. BREAKING: `Remote.ls()` → `list[str]`.
  The bucket_policy_only gotcha (line above) is now baked into the gs:// path.
- **Stress-tested 2026-08-15** (devbox tier; repeatable suite at
  `packages/ferry/scripts/stress.py`, merged PR #40 with the CI fix — arsenal
  integration tests must SELF-GATE on an env var, CI runs plain `pytest`):
  ~195 MiB/s sustained (7.1 GiB/110 files, transfers=16); kill -9 + re-pull →
  0 byte diffs (rclone check), resume is FILE-granular (partial files restart
  from zero — fine for sharded weights, bad for one giant file); 52k tiny
  files = request-rate-bound ~130 obj/s (tar tiny-file datasets first).
  Pod-tier stress PASSED same day (see below).
- **v0.3.1 (arsenal PR #41 MERGED 2026-08-15): the [[bellhop-library]]
  pairing.** `ferry.gcs_pod_env(name="gcs")` mints a ~1h token from local
  gcloud ADC → rclone env-config vars for `RunSpec(env=...)`; no long-lived
  secret on the pod (this box has NO GCS SA key — ADC is authorized_user, do
  not ship that file to pods). Pod-tier stress
  (`packages/ferry/scripts/stress_pod.py`, RTX 4090 COMMUNITY): PyPI install +
  ensure_rclone bootstrap + token-only auth PASSED — 7.1 GiB @ 57 MiB/s,
  kill-resume 110/110 matching, clean teardown. CAVEAT: community-pod net ≈
  57 MiB/s → 200 GB ≈ 1 h ≈ token TTL; largest jobs want a scoped SA key.
  Recipe documented in bellhop README ("Big data on the pod: pair with
  ferry").
- Pairs with the [[gcs-experiment-storage-convention]] (gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/).
