# Thought capture (`mailroom`): ingestion pipeline — MVP spec

*2026-08-17 · agent-drafted, standing until Daniel edits · companion to
[`threads.md`](threads.md); design decisions in this doc are Daniel's
(stated 2026-08-17) unless marked otherwise*

## What this is

An arsenal package — working name **`mailroom`** (Daniel may rename; the
building metaphor: things arrive from outside, get sorted, routed to the
right floor) — that ingests Daniel's captured thoughts from their three
native surfaces and routes them onto the spines that already exist:

```
Todoist Inbox ──┐
Slack lab-notes ─┼─ingest──▶ thought spool ──triage──▶ route/act ──▶ existing spines
voice memos ────┘            (~/.mailroom/)  (haiku)      │           (threads notes, Todoist
                                                          │            projects, goals/, papers,
                                                          │            flare, candidate threads)
                                                          └─▶ loop-closure mark at the source
                                                              + daily digest (veto surface)
```

`threads` is bottom-up state from **agent** transcripts; `mailroom` is
bottom-up state from **Daniel** utterances. Same pipeline shape, same
philosophy (draft-and-veto: reversible actions run without pre-approval;
veto = delete/rework), same cardinal rule: **no second registry** — a
thought *resolves onto* Todoist projects, memory slugs, goal files, or the
papers queue; the spool keeps only provenance.

## Standing decisions (Daniel, 2026-08-17)

1. **Separate from `threads` for now.** Likely future unification: both
   feed one personal knowledge base (Obsidian-style vault — `threads`
   already mirrors to `~/.threads/vault/`, arsenal issue #49). MVP keeps
   the tools separate but the spool schema vault-friendly (markdown +
   frontmatter mirror is a cheap phase 2).
2. **Todoist is capture-only and should be drained.** Daniel's explicit
   goal is periodically draining it to zero; the adapter owns that drain
   rather than waiting for him to do it.
3. **Voice memos**: an automation that queries the memos, transcribes with
   **NVIDIA Parakeet**, and stashes raw provenance.
4. **Slack**: multi-channel capable by config; MVP limited to
   `#lab-notes-daniel`.

## Adapters

All adapters are cron-driven, incremental (per-source cursor in
`state.json`), and idempotent — a no-change re-run does nothing.

### Slack (`#lab-notes-daniel`, multi-channel by config)

- `channels = ["lab-notes-daniel"]` in `~/.mailroom/config.toml`; adding a
  channel is a config edit, no code.
- Ingest **Daniel-authored messages** since the cursor (thread replies
  included; other users' messages ignored). Slack-transcribed audio clips
  ride along for free.
- **Loop closure**: react ✅ on ingested messages; when a thought triggers a
  non-obvious route (e.g. seeded a candidate thread), a short threaded
  reply says where it went (knob: `reply_on_route`, default on).
- **Credential** (DONE 2026-08-17/18): the claude.ai Slack MCP is
  interactive-only — the cron uses the `jarvis-mailroom` Slack app (bot
  `U0BQWRJETGR`; scopes `channels:history`, `channels:read`,
  `groups:history`, `groups:read`, `reactions:write`, `chat:write`,
  `files:read`), invited to `#lab-notes-daniel` (`C0B5RUX4P26`, private);
  `SLACK_MAILROOM_TOKEN` in `~/.env`. History read, reactions.add, and
  file download all verified live.

### Todoist (capture-only → drain to zero)

The drain's primitive is **file, not complete** (Daniel's explicit
concern, 2026-08-17: never check off things that didn't actually get
done). "Routed" never means "done"; completing a task remains exclusively
Daniel's act. Concretely:

- **Actionable items stay open.** A todo-type Inbox item is *moved* to
  the right curated project with a comment `mailroom: filed from Inbox`.
  Todoist stays the canonical personal task tracker; the Inbox drains to
  zero mostly via moves, not completions.
- **Close-with-comment is reserved for non-task captures whose content
  has been transferred to a spine with its own liveness tracking** — a
  research idea that became a threads note or goal bullet (tracked by
  dormancy flags / `/goal-review`), a paper that became a *new open task*
  in Papers-to-read, a duplicate of an existing item. The closing comment
  links the destination; the full text is already in the spool. Closure
  here is custody transfer to a *better-tracked* home, never completion —
  an idea rotting in the Inbox has zero liveness machinery; a threads
  note has dormancy flags.
- If triage is unsure whether something is a task, it is treated as a
  task (moved, kept open) — the failure mode of filing a note as a task
  is clutter; the failure mode of closing a task as a note is lost work.
- Items that triage can't place at all stay open in the Inbox, labeled
  `mailroom-unclear`, and appear in the digest — the Inbox never silently
  accumulates unprocessed items, and nothing is ever deleted.
- The daily digest lists every move and every closure separately;
  reopen/re-file is the veto.
- **Stale sweep** (propose-only): items in curated projects untouched
  for N days (default 60) are listed in the digest as prune candidates.
  The curated projects are Daniel's; mailroom never closes items outside
  the Inbox.
- **Credential** (DONE 2026-08-18): `TODOIST_API_TOKEN` in `~/.env`,
  verified. **Build note: Todoist REST v2 is HTTP 410 Gone — use the
  unified API `https://api.todoist.com/api/v1/` (cursor-paginated
  `{results, next_cursor}` envelopes).** Inbox project id
  `6RJ8MCM4gr9C9WpJ`; drain baseline 2026-08-18: 52 open Inbox items,
  30 older than 30 days.

### Voice memos (Slack transport → Parakeet → provenance)

- **Transport (Daniel's pick, 2026-08-18): audio rides the Slack
  adapter** — record directly in `#lab-notes-daniel` (mic icon; ~5-min
  clip cap) or share a Voice Memos recording into the channel (long /
  offline recordings). Zero extra credentials: the mailroom bot token
  carries `files:read`, and the whole leg was verified end-to-end
  2026-08-18 (real clip → `url_private_download` with bot token →
  ffmpeg 16 kHz mono → Parakeet transcript). The earlier
  Shortcut→Drive→rclone design is the *upgrade path* if one-tap sharing
  ever annoys (it needs a `drive:` rclone remote; the claude.ai Drive
  connector is interactive-only, unusable from cron).
- **Transcription: Parakeet** (`nvidia/parakeet-tdt-0.6b-v2`) via
  **`onnx-asr[cpu,hub]`** — no NeMo dependency; verified on this (GPU-less)
  box: ~8 s model load, sub-realtime inference on clips. Slack's own
  auto-transcription, when present, is kept alongside as a cross-check
  field. Model choice isolated behind a `transcribe(audio) -> text` seam;
  a large backfill batch goes to a bellhop pod.
- **Provenance**: original audio mirrored to
  `gs://alignment-team-general-storage/daniel/jarvis/mailroom/audio/`
  (pointer in the thought record), transcript in the spool. Nothing is
  deleted at the source.

## Thought record (normalize)

`~/.mailroom/thoughts/<id>.json` (spool pattern of `~/.flare/`,
`~/.threads/`):

```json
{
  "id": "…", "source": "slack|todoist|voice", "ts": "…",
  "permalink": "message URL | task id | gs:// audio path",
  "raw": "text | transcript",
  "triage": {
    "type": "todo|thread-note|research-idea|goal-signal|paper|admin|unclear",
    "title": "one line",
    "candidate_slugs": ["from MEMORY.md index shown in-prompt"],
    "goal": "goal file if goal-signal", "urgency": "low|high"
  },
  "route": {"action": "…", "target": "…", "at": "…"}
}
```

Triage is one haiku-class `claude -p` call per thought (JSON-schema
output), batched, with the same cost guardrails as `threads scan`
(per-run cap, flare a warn on truncation). Same auth gotcha applies:
non-login shells must source `~/.env` for `ANTHROPIC_API_KEY`.

## Routing — the actuator table

| Triage type | Action (MVP rung) |
|---|---|
| thread-note (names ongoing work) | `threads note <slug>` — lands on the thread, shows in dashboard + `pickup` |
| todo | Todoist task in the right curated project (voice/Slack origin) or re-file the Inbox item |
| research-idea, no home | seed a candidate thread (threads machinery) or dated Parked-follow-ups bullet on the owning goal |
| goal-signal | dated bullet in the goal file's Frontier / Parked follow-ups (direct commit to main, matching how wrap-ups append) |
| paper | Todoist "Papers to read" + arxivist fetch when an arXiv id is present |
| urgent / blocked | `flare` |
| admin | Todoist Inbox→appropriate project; nothing clever |
| unclear | stays at source (labeled) + digest |

**Empowerment ladder** (mirrors goals/ automation): everything above is
reversible and runs without pre-approval under draft-and-veto. The top
rung — a thought like "we should sweep X vs Y" becoming a dispatched
concierge task — is **propose-only at MVP**: mailroom drafts the spec and
parks it in the digest; flipping any auto-dispatch waits for Daniel's
explicit call, per goals/README ladder rules.

## Digest — the veto surface

- `mailroom render` — markdown digest: thoughts ingested, route taken per
  thought, Todoist drain delta (Inbox n→m), stale-sweep prune candidates,
  unclear items, proposed (not dispatched) task specs.
- Daily cron posts the digest headline through `flare --sev info` when
  the day was non-empty; full page served via lobby
  (`mailroom serve` → `/a/mailroom/`) or read in the spool.
- Veto = undo the route (reopen the Todoist item, delete the note/bullet)
  and, when it reflects a policy, tell mailroom — routing rules live in
  `config.toml`, not code, so corrections are config edits.

## Storage

`~/.mailroom/`: `thoughts/*.json`, `audio/` (local cache; GCS is the
durable copy), `config.toml`, `state.json` (cursors). Spool is retained,
not a cache (sources age out or get drained). Vault mirror
(markdown + frontmatter, Obsidian-compatible, regenerable) is phase 2 and
the convergence point with `~/.threads/vault/`.

## Cron

Once built: `ops/cron.tab` entry, every 2h,
`set -a; . ~/.env; set +a && mailroom ingest && mailroom route`, plus a
daily digest run. Never installed by hand (`ops/install-cron.sh`).

## Definition of done (MVP)

Gate-checkable:

1. **Slack**: backfill of `#lab-notes-daniel` (last 90 days) ingested;
   every Daniel message has a thought record; new messages picked up on
   the next run; ✅ marks visible in-channel. Re-run with no new messages
   is a no-op in <5 s.
2. **Todoist**: one drain run takes the real Inbox to 0 (minus
   `mailroom-unclear` items), every moved item carrying its filing
   comment and every closed item a transfer comment linking its
   destination; the move/close split and drain delta are reported, not
   asserted. Zero completions of task-typed items.
3. **Voice**: ≥1 real clip flows end-to-end through the built tool
   (Slack audio file → download → Parakeet → thought record with GCS
   audio pointer). The raw path (download → ffmpeg → onnx-asr Parakeet
   CPU transcript) was already proven by hand on 2026-08-18.
4. **Routing**: ≥80% of backfilled thoughts auto-routed (not `unclear`);
   actual rate reported. At least one thought lands as a `threads note`
   and one as a goal-file bullet to demonstrate the actuators.
5. Digest live (lobby URL delivered) + daily cron entries merged in
   `ops/cron.tab`; total model spend for the backfill reported.

Suggested concierge gate:
`PrOpen() & ShellOk("mailroom ingest --check && mailroom route --check")`.

## Non-goals (MVP)

- PKM/vault unification with threads (phase 2; Daniel-flagged future
  direction).
- Auto-dispatching concierge tasks from thoughts (propose-only rung).
- WhatsApp ingestion (bridge parked, jarvis #128), DMs-to-self, other
  Slack channels beyond the config default.
- Embeddings/semantic search over the spool; real-time (cron cadence is
  enough for thoughts).
- Closing/editing anything in Todoist curated projects (propose-only
  stale sweep).

## Phase 2 sketch (not committed)

Vault mirror + merge with `~/.threads/vault/` into one PKM base →
desk section for unclear/proposed items → routing-quality feedback loop
(vetoes observed → config suggestions) → auto-dispatch rung per-type
behind explicit Daniel flip → additional channels/sources by config.
