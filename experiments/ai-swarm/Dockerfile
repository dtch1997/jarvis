# Agent sandbox image: node + claude CLI + codex CLI + basic coding toolchain.
# Agents run as an unprivileged uid with HOME=/home/agent (bind-mounted).
FROM node:22-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git python3 python3-venv curl ca-certificates jq ripgrep procps \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code @openai/codex \
    && mkdir -p /home/agent /workspace /comms \
    && chmod 777 /home/agent /workspace /comms

ENV HOME=/home/agent
WORKDIR /workspace
