#!/usr/bin/env bash
# Rebuild the experiment venv (driver deps live outside the workspace venv
# because tinker/transformers pins shouldn't leak into jarvis tools).
# Usage: VENV=/path/to/venv bash setup_env.sh
set -euo pipefail
VENV="${VENV:-.venv-exp}"
uv venv "$VENV" --python 3.11
uv pip install --python "$VENV/bin/python" \
  tinker transformers jinja2 datasets httpx xy \
  -e "$(git rev-parse --show-toplevel)/jarvis-tools/packages/stagehand"
echo "venv ready: $VENV"
