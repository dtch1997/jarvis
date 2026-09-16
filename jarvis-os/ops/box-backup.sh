#!/usr/bin/env bash
# Nightly box-state backup → GCS. The box must be recoverable from
# (1) the jarvis + jarvis-memory git repos and (2) this backup alone;
# ops/bootstrap-box.sh is the restore path.
#
#   ops/box-backup.sh            snapshot + upload + prune old snapshots
#   ops/box-backup.sh --dry-run  build the tarball, print contents, no upload
#
# What goes in: the durable state that is NOT already in a git repo —
# ~/jarvis-data (ledgers, pod-digest, salvaged pod archives), ~/.threads,
# ~/.flare, ~/.desk spools, ~/.config/{gazette,desk}, the harness memory
# (~/.claude/projects/*/memory + settings), and a crontab snapshot
# (informational — install-cron.sh regenerates it from the repo).
#
# What stays out, deliberately: SECRETS (~/.env, ~/.config/flare/config.toml
# — the GCS bucket is team-readable; bootstrap-box.sh recreates templates and
# the keys are re-pasted by Daniel), ~/jarvis-memory (its own private repo,
# pushed nightly by the 03:41 cron), the repos themselves, and venvs.
set -euo pipefail

BUCKET="gs://alignment-team-general-storage/daniel/jarvis/box-backup"
KEEP_DAYS=14
STAMP="$(date -u +%F)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

crontab -l > "$TMP/crontab.snapshot" 2>/dev/null || true

# tar exits 1 on "file changed as we read it" (live spools) — tolerate 1, not 2+.
set +e
tar czf "$TMP/state-$STAMP.tar.gz" -C "$HOME" \
    --exclude='.claude/projects/*/memory/__pycache__' \
    --ignore-failed-read \
    jarvis-data .threads .flare .desk \
    .config/gazette .config/desk \
    .claude/projects/*/memory .claude/settings.json \
    -C "$TMP" crontab.snapshot 2>/dev/null
rc=$?
set -e
[ "$rc" -le 1 ] || { flare "box-backup: tar failed rc=$rc" --sev warn || true; exit "$rc"; }

if [ "${1:-}" = "--dry-run" ]; then
    tar tzf "$TMP/state-$STAMP.tar.gz" | head -40
    du -h "$TMP/state-$STAMP.tar.gz"
    exit 0
fi

if ! gcloud storage cp -q "$TMP/state-$STAMP.tar.gz" "$BUCKET/nightly/state-$STAMP.tar.gz"; then
    flare "box-backup: upload to GCS failed (gcloud auth expired?)" --sev warn || true
    exit 1
fi

# Prune snapshots older than KEEP_DAYS (names are date-stamped, lexically sortable).
cutoff="$(date -u -d "-$KEEP_DAYS days" +%F)"
gcloud storage ls "$BUCKET/nightly/" 2>/dev/null | while read -r obj; do
    d="$(basename "$obj" | sed -n 's/^state-\([0-9-]\{10\}\)\.tar\.gz$/\1/p')"
    if [ -n "$d" ] && [ "$d" \< "$cutoff" ]; then
        gcloud storage rm -q "$obj" || true
    fi
done

echo "box-backup: $STAMP ok ($(du -h "$TMP/state-$STAMP.tar.gz" | cut -f1))"
