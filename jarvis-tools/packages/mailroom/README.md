# mailroom

Thought-capture ingestion. `mailroom` is to **Daniel's utterances** what
`threads` is to **agent transcripts**: it ingests captures from their three
native surfaces and routes them onto the spines that already exist — no
second registry. Companion spec: `jarvis-os/docs/thought-capture.md`.

```
Todoist Inbox ──┐
Slack lab-notes ─┼─ ingest ─▶ thought spool ─ triage ─▶ route ─▶ Todoist projects,
voice memos ────┘            (~/.mailroom/)   (haiku)            threads notes, goal
                                                                 bullets, papers, flare
```

## CLI

```sh
set -a; . ~/.env; set +a
mailroom ingest          # pull new Slack/Todoist/voice captures into the spool (+ ✅)
mailroom route           # triage each and act on the right spine
mailroom render [--stale] # markdown digest (the veto surface); --stale lists prune candidates
mailroom status          # gate summary for both stages
mailroom serve           # lobby dashboard at /a/mailroom/
mailroom ingest --check  # gate: every source item has a record & re-run is a no-op
mailroom route  --check  # gate: ≥80% routed, drain delta recorded, zero task-completions
```

## Adapters (incremental, idempotent, cron-driven)

- **Slack** (`#lab-notes-daniel`, multi-channel by `config.toml`) — ingests
  Daniel-authored messages + his thread replies since a per-channel cursor;
  ignores the bot's own and other automations' posts. Loop closure = ✅
  reaction, tracked in `state.json` so re-runs never re-hit the API. On
  incremental runs a threaded reply notes where a thought went
  (`reply_on_route`, off during backfill).
- **Todoist** (unified API v1) — **files, never completes.** Task-typed Inbox
  items are *moved* to a curated project (kept open) with a filing comment;
  close-with-comment is reserved for non-task captures whose content
  transferred to a better-tracked spine; unplaceable items stay in the Inbox
  labeled `mailroom-unclear`. Nothing outside the Inbox is ever touched
  (the stale sweep is propose-only, digest-listing).
- **Voice** — audio rides the Slack adapter; downloaded with the bot token,
  transcoded `ffmpeg -ar 16000 -ac 1`, transcribed by NVIDIA Parakeet
  (`nemo-parakeet-tdt-0.6b-v2`). onnx-asr/onnxruntime don't build on the 3.14
  workspace venv, so transcription is isolated behind `transcribe.py` into a
  dedicated 3.12 venv (see below). Original audio is mirrored to GCS; the
  record keeps the `gs://` pointer and Slack's own auto-transcript as a
  cross-check.

## Voice venv (one-time)

```sh
uv venv --python 3.12 ~/.cache/mailroom-asr-venv
VIRTUAL_ENV=~/.cache/mailroom-asr-venv uv pip install "onnx-asr[cpu,hub]"
```

`transcribe.py` shells into `$MAILROOM_ASR_PYTHON` (default
`~/.cache/mailroom-asr-venv/bin/python`). A large backfill batch can point that
at a bellhop pod instead.

## Storage

`~/.mailroom/`: `thoughts/*.json` (one record per capture, provenance +
triage + route), `audio/` (local cache; GCS is durable), `state.json`
(cursors, reacted set, drain baseline), `config.toml` (routing policy — edit
here, not in code), `digest.md`. Gate `--check` commands read only the spool
and never write or call a model.
