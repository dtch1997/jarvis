#!/usr/bin/env bash
# Bootstrap (or recover) a jarvis box from nothing. One line on fresh Ubuntu:
#
#   curl -fsSL https://raw.githubusercontent.com/dtch1997/jarvis/main/jarvis-os/ops/bootstrap-box.sh | bash
#
# Idempotent — safe to re-run; each step no-ops if already done. Interactive
# only where auth genuinely needs a human (gh auth login, gcloud auth login,
# pasting secrets into ~/.env).
#
# What it rebuilds: repos (~/jarvis, ~/jarvis-memory), the uv workspace +
# CLI symlinks, state from the latest GCS nightly (ops/box-backup.sh),
# secret templates (~/.env, ~/.config/flare/config.toml), and the crontab.
set -euo pipefail

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
need_manual=()

say "1/7 base tools"
command -v git >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq git; }
command -v curl >/dev/null || sudo apt-get install -y -qq curl
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v gh >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq gh; }
export PATH="$HOME/.local/bin:$PATH"

say "2/7 github auth"
if ! gh auth status >/dev/null 2>&1; then
    echo "gh is not authenticated — running 'gh auth login' (choose SSH protocol)."
    gh auth login
fi

say "3/7 repos"
[ -d "$HOME/jarvis/.git" ] || git clone git@github.com:dtch1997/jarvis.git "$HOME/jarvis"
[ -d "$HOME/jarvis-memory/.git" ] || git clone git@github.com:dtch1997/jarvis-memory.git "$HOME/jarvis-memory"

say "4/7 workspace + CLIs"
(cd "$HOME/jarvis" && uv sync --all-packages)
bash "$HOME/jarvis/jarvis-tools/ops/link-clis.sh"

say "5/7 state restore from GCS"
if ! command -v gcloud >/dev/null; then
    echo "installing google-cloud-cli (snap)…"
    sudo snap install google-cloud-cli --classic || need_manual+=("install gcloud, then: gcloud auth login && gcloud auth application-default login")
fi
if command -v gcloud >/dev/null; then
    gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q . || {
        echo "gcloud is not authenticated — running 'gcloud auth login'."
        gcloud auth login --no-launch-browser
    }
    BUCKET="gs://alignment-team-general-storage/daniel/jarvis/box-backup"
    latest="$(gcloud storage ls "$BUCKET/nightly/" 2>/dev/null | sort | tail -1 || true)"
    if [ -n "$latest" ]; then
        echo "restoring $latest"
        tmp="$(mktemp -d)"
        gcloud storage cp -q "$latest" "$tmp/state.tar.gz"
        tar xzf "$tmp/state.tar.gz" -C "$HOME" --skip-old-files
        rm -rf "$tmp"
    else
        echo "no nightly snapshot found under $BUCKET/nightly/ — skipping restore."
    fi
fi

say "6/7 secret templates (fill by hand — never backed up)"
mkdir -p "$HOME/.config/flare"
if [ ! -s "$HOME/.env" ]; then
    cat > "$HOME/.env" <<'EOF'
# Fill these in (see jarvis-memory/jarvis-new-box-setup.md for where each
# comes from). chmod 600.
RUNPOD_API_KEY=
ANTHROPIC_API_KEY=
SLACK_MAILROOM_TOKEN=
TODOIST_API_TOKEN=
EOF
    chmod 600 "$HOME/.env"
    need_manual+=("fill ~/.env (RunPod / Anthropic workspace-scoped / Slack bot / Todoist)")
fi
if [ ! -s "$HOME/.config/flare/config.toml" ]; then
    cat > "$HOME/.config/flare/config.toml" <<'EOF'
# flare Slack transport: mailroom bot token + #jarvis-dev channel id.
[slack]
bot_token = ""
channel = "C0BQSU87ACD"
EOF
    chmod 600 "$HOME/.config/flare/config.toml"
    need_manual+=("paste the Slack bot token into ~/.config/flare/config.toml")
fi

say "7/7 crontab"
mkdir -p "$HOME/.claude/logs" "$HOME/jarvis-data/pod-digest"
bash "$HOME/jarvis/jarvis-os/ops/install-cron.sh"

say "done"
if [ "${#need_manual[@]}" -gt 0 ]; then
    echo "manual steps remaining:"
    printf '  - %s\n' "${need_manual[@]}"
fi
echo "sanity checks: flare 'bootstrap test' --sev info · gazette version status · desk render"
