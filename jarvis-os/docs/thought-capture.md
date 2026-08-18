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
- **Credential**: the claude.ai Slack MCP is interactive-only — a cron
  needs a real token. Small Slack app with `channels:history`,
  `channels:read`, `reactions:write`, `chat:write`, bot invited to the
  channel; token as `SLACK_MAILROOM_TOKEN` in `~/.env`.
  `BLOCKED-ON-DANIEL:` create the Slack app + drop the token in `~/.env`
  (same app can later carry the flare webhook, which is also unconfigured).

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
- **Credential**: Todoist REST API token as `TODOIST_API_TOKEN` in
  `~/.env`. `BLOCKED-ON-DANIEL:` copy it from Todoist →
  Settings → Integrations → Developer.

### Voice memos (query → Parakeet → provenance)

- **Transport (recommended; needs a one-time setup):** an iOS Shortcuts
  personal automation uploads new Voice Memos recordings to a Google
  Drive folder (`VoiceMemos-inbox/`); the devbox pulls via rclone.
  `BLOCKED-ON-DANIEL:` (a) set up the Shortcut on the phone (iOS 18
  Shortcuts exposes Voice Memos recordings; agent drafts the shortcut
  steps), (b) one-time `rclone config` OAuth for a `drive:` remote on the
  devbox (only `gcs:` exists today). Fallback transport if the Shortcut
  route disappoints: record/forward audio clips into Slack, which the
  Slack adapter already ingests.
- **Transcription: Parakeet** (`nvidia/parakeet-tdt-0.6b-v2`, NeMo). No
  GPU on this box — CPU inference is acceptable for memo-length audio
  (minutes, not hours); a large backfill batch goes to a bellhop pod
  instead. Model choice isolated behind a `transcribe(audio) -> text`
  seam.
- **Provenance**: original audio mirrored to
  `gs://alignment-team-general-storage/daniel/jarvis/mailroom/audio/`
  (pointer in the thought record), transcript in the spool. Nothing is
  deleted from the phone.

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
3. **Voice**: ≥1 real memo flows end-to-end (phone → Drive → rclone →
   Parakeet → thought record with GCS audio pointer) — this leg is
   allowed to lag the others on the `BLOCKED-ON-DANIEL` setup steps, and
   ships behind them without blocking the MVP PR.
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
