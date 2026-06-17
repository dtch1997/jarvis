#!/usr/bin/env bash
# Rung-0 constitutional-audit run commands (Anthropic soul doc).
# All model roles → OpenRouter (one key). See spec.md / decisions.md.
#
# Usage:
#   ./run_audit.sh smoke      # 2 tenets x 6 turns, old target only  (~$0.50, wiring check)
#   ./run_audit.sh old        # full 7-tenet slice vs sonnet-4   (old generation)
#   ./run_audit.sh new        # full 7-tenet slice vs sonnet-4.6  (new generation)
#   ./run_audit.sh noise      # epochs=3 on a 2-tenet subset of the old model (variance)
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
set -a; source ~/.env; set +a   # export OPENROUTER_API_KEY (+ others)

AUDITOR=openrouter/anthropic/claude-sonnet-4.5
JUDGE=openrouter/anthropic/claude-sonnet-4.5
OLD=openrouter/anthropic/claude-sonnet-4        # high-violation generation (VIOLATION_MAP: 27)
NEW=openrouter/anthropic/claude-sonnet-4.6      # low-violation generation  (VIOLATION_MAP: 2)
MT=${MT:-15}                                    # max_turns (paper: 30; Rung-0: 15)
CONN=${CONN:-6}

run () { # role_target  save_subdir  extra_inspect_args...
  local target="$1"; local sub="$2"; shift 2
  inspect eval audit_slice.py \
    --model-role auditor="$AUDITOR" \
    --model-role target="$target" \
    --model-role judge="$JUDGE" \
    -T max_turns="$MT" -T transcript_save_dir="./results/$sub" \
    --log-dir "./results/${sub}_logs" --max-connections "$CONN" "$@"
}

case "${1:-}" in
  smoke) run "$OLD" smoke -T limit=2 -T max_turns=6 ;;
  old)   run "$OLD" sonnet4 ;;
  new)   run "$NEW" sonnet46 ;;
  noise) run "$OLD" noise_sonnet4 -T only=T5.6a --epochs 3 ;;
  *) echo "usage: $0 {smoke|old|new|noise}"; exit 2 ;;
esac
