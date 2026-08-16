#!/usr/bin/env bash
# Reconcile the live crontab's managed block with ops/cron.tab.
#
#   ops/install-cron.sh           install/refresh the managed block (idempotent)
#   ops/install-cron.sh --check   exit 0 if live block matches ops/cron.tab,
#                                 else print a diff and exit 1 (used by the
#                                 weekly thesis-review refresh to detect drift)
#
# Owns ONLY the lines between the BEGIN/END markers below; everything else in
# the user's crontab is left untouched.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAB="$REPO/ops/cron.tab"
BEGIN="# BEGIN ArcadiaImpact/jarvis (managed by ops/install-cron.sh; edit ops/cron.tab, not this block)"
END="# END ArcadiaImpact/jarvis"

[[ -f "$TAB" ]] || { echo "missing $TAB" >&2; exit 2; }

desired="$(cat "$TAB")"
current="$(crontab -l 2>/dev/null || true)"

live_block="$(printf '%s\n' "$current" | awk -v b="$BEGIN" -v e="$END" '
  $0 == e { inblock = 0 } inblock { print } $0 == b { inblock = 1 }')"

if [[ "${1:-}" == "--check" ]]; then
  if diff -u <(printf '%s\n' "$desired") <(printf '%s\n' "$live_block") >/tmp/cron-drift.$$; then
    rm -f /tmp/cron-drift.$$
    echo "cron block in sync with ops/cron.tab"
    exit 0
  else
    echo "DRIFT between ops/cron.tab (-) and live crontab block (+):"
    cat /tmp/cron-drift.$$
    rm -f /tmp/cron-drift.$$
    echo "fix: run ops/install-cron.sh (after PR-reviewing any cron.tab change)"
    exit 1
  fi
fi

rest="$(printf '%s\n' "$current" | awk -v b="$BEGIN" -v e="$END" '
  $0 == b { inblock = 1 } !inblock { print } $0 == e { inblock = 0 }')"

{ printf '%s\n' "$rest" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}'
  printf '%s\n%s\n%s\n' "$BEGIN" "$desired" "$END"
} | crontab -

echo "installed managed cron block from ops/cron.tab"
