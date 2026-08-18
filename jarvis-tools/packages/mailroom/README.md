# mailroom — thought-capture ingestion

`mailroom` ingests Daniel's captured thoughts from their three native surfaces
and routes them onto the spines that already exist. It is the sibling of
[`threads`](../threads): same pipeline shape (ingest → spool → triage → route),
same draft-and-veto philosophy, same cardinal rule — **no second registry**: a
thought *resolves onto* Todoist projects, memory/thread slugs, goal files, or
the papers queue; the spool keeps only provenance. `threads` observes agent
transcripts; `mailroom` observes Daniel's utterances.

```
Todoist Inbox ──┐
Slack lab-notes ─┼─ ingest ─▶ thought spool ─ triage ─▶ route/act ─▶ existing spines
voice memos ────┘            (~/.mailroom/)   (haiku)     │           (threads notes, Todoist
                                                          │            projects, goals/, papers, flare)
                                                          └─▶ ✅ loop-closure at the source + daily digest
```

## CLI

```
mailroom ingest [--backfill] [--check]   # pull captures into the spool (✅ reactions)
mailroom route  [--dry-todoist] [--check] # triage + land each on a spine
mailroom render [--no-stale]             # the digest (veto surface), markdown
mailroom serve                           # digest via the lobby hub → /a/mailroom/
mailroom status                          # one-line pipeline + gate summary
```

- **`ingest --check`** — fails unless every source item since backfill start
  already has a thought record (a re-run would be a no-op); no model calls, no
  transcription.
- **`route --check`** — fails unless ≥ `route_threshold` (default 80%) of
  thoughts are routed (not `unclear`), the Todoist drain delta is recorded, and
  **zero task-completions** are logged.

## Adapters

- **Slack** (`#lab-notes-daniel`, multi-channel by config) — ingests
  **Daniel-authored** messages only (top-level + his thread replies); the bot's
  own posts and every other bot/user in the channel (gazette, desk, flare) are
  ignored. Loop closure = ✅ reaction on each ingested message; `reply_on_route`
  posts a short threaded reply on *newly-ingested* messages (never on the
  backfill).
- **Todoist** (unified API `v1`; REST v2 is 410 Gone) — the Inbox is capture-only
  and drained to zero. **File, never complete**: task-typed items are *moved* to
  a curated project (stay open, filing comment); close-with-comment is reserved
  for non-task captures whose content transferred to a better-tracked spine.
  Unplaceable items are labeled `mailroom-unclear` and stay. Nothing outside the
  Inbox is mutated (the stale sweep is propose-only, digest listing only);
  nothing is ever deleted.
- **Voice** — audio rides the Slack adapter; downloaded with the bot token,
  transcoded `ffmpeg -ar 16000 -ac 1`, transcribed with Parakeet
  (`onnx-asr[cpu,hub]`, model `nemo-parakeet-tdt-0.6b-v2`) behind a
  `transcribe(wav)->str` seam, mirrored to GCS (pointer in the record). Slack's
  own auto-transcription is kept as a cross-check field. Install the extra for
  the live leg: `uv pip install 'mailroom[voice]'`.

## Storage

`~/.mailroom/` (override the base with `MAILROOM_HOME`): `thoughts/*.json`
(retained provenance), `audio/` (local cache; GCS is durable), `config.toml`
(tunable knobs — routing corrections are config edits, not code), `state.json`
(per-source cursors + run stats). Triage is one batched haiku `claude -p` call
(isolated `CLAUDE_CONFIG_DIR`, ambient `ANTHROPIC_API_KEY`), with a per-run
call cap that flares on truncation.

Credentials come from the environment (`~/.env`): `SLACK_MAILROOM_TOKEN`,
`TODOIST_API_TOKEN`, `ANTHROPIC_API_KEY`.
