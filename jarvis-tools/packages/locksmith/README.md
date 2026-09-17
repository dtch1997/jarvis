# locksmith

Credential files as build artifacts: sync `~/.env` and friends to cloud
storage as **one Fernet-encrypted tarball**, so a new box bootstraps from
one hand-carried key instead of six hand-copied files. Proposed in
[jarvis#246](https://github.com/dtch1997/jarvis/issues/246) after the
2026-09 runtime migration showed credentials were the only state with no
remote.

```bash
locksmith init     # once: generates ~/.config/locksmith/{key,config.toml}
locksmith push     # tar manifest files -> encrypt -> <remote>/bundle.enc (+history/)
locksmith status   # local items, key presence, remote bundle timestamp
# new box: copy ~/.config/locksmith/key over, then
locksmith pull     # download -> decrypt -> restore (existing files backed up)
```

- The manifest and remote live in `~/.config/locksmith/config.toml`
  (default remote: `gcs:.../daniel/jarvis/locksmith` via rclone).
- The **key is never synced** — it is the one root credential you carry.
- Nothing secret is ever printed; output is paths, sizes, timestamps.
- Transport is `rclone`, so it works wherever ferry works (env_auth /
  ADC), independent of `gcloud` login state.
- GCP Secret Manager was considered ([#246](https://github.com/dtch1997/jarvis/issues/246));
  it needs project-level IAM the box's identity currently lacks. The
  backend seam is `_rclone()` + `make_bundle()` — swappable later.
