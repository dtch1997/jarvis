#!/usr/bin/env bash
# Mirror all ARCH run transcripts from S3 to a local raw store.
# Credentials: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from ~/.env (auto-run keys).
# Buckets per Alejandro (Slack #arch, 2026-09-02):
#   - arch2-154723392477-eu-north-1-an  — legacy, most historical runs
#   - arcadia-arch-transcripts          — new standardized transcript bucket
set -euo pipefail
RAW="${1:-$HOME/data/arch-transcripts/raw}"
mkdir -p "$RAW"/{arch2-legacy,arch2-legacy-heldout,arcadia-arch-transcripts}

set -a; . ~/.env; set +a

aws s3 sync s3://arch2-154723392477-eu-north-1-an/arch2/        "$RAW/arch2-legacy/"             --only-show-errors
aws s3 sync s3://arch2-154723392477-eu-north-1-an/arch-heldout/ "$RAW/arch2-legacy-heldout/"     --only-show-errors
aws s3 sync s3://arcadia-arch-transcripts/                      "$RAW/arcadia-arch-transcripts/" --only-show-errors

# some runs (judge-cot) uploaded transcripts as tarballs — extract in place
find "$RAW" -name 'claude-transcripts.tgz' | while read -r tgz; do
  d="$(dirname "$tgz")"
  [ -d "$d/projects" ] || tar xzf "$tgz" -C "$d"
done

echo "raw mirror complete: $RAW"
du -sh "$RAW"/*
