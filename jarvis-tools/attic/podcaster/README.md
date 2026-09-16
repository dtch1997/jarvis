# podcaster

**A topic goes in. A podcast episode you would actually listen to comes out.**

```bash
podcaster make "training cooperativeness" --minutes 12 --publish
```

Three passes — research, write, narrate — each usable on its own, and one
declared [stagehand](../stagehand) flow when you want all of it:

```
plan ──> questions ──> dig (fan-out, retried) ──> brief ──> script (style-gated)
                                                              │
                                        segments <─────────────┘
                                            │
                                        narrate (fan-out) ──> master ──> MP3
```

## Why it isn't just "ask a model for a script and read it aloud"

Two things separate audio you finish from audio you switch off.

**An angle, not a topic.** The research pass picks one specific claim or tension
*before* it searches (`plan_angle`), then fans out one web-researched question
per beat — including one hunting the strongest case *against* the angle — and
demands findings that contain numbers, names, dates or quotes. Findings carry
their source URL, which becomes the show notes and never the narration.

**A style gate, not a style request.** Models write for the page by default:
bullets, 45-word sentences, "as discussed above", parenthetical citations, URLs.
Prompting against that regresses; gating against it holds. `podcaster.style`
audits every draft mechanically — mean sentence length, overlong sentences, page
furniture, cold-open/sign-off structure, is a listener actually addressed, is the
thing the length that was asked for — and failures go back to the writer as the
next draft's feedback (`stagehand.with_retry`). The same gate runs offline:

```bash
podcaster audit script.json     # exit 1 + the list of what makes it unlistenable
```

`podcaster.speakable` then handles the last mile before the voice, which is a
different job: markdown out, addresses out, `e.g.` → "for example", `85%` → "85
percent", `RLHF` → "R L H F", em-dashes into pauses a voice actually renders.

## Narration

Piper (VITS, ONNX) on CPU: real-time factor ≈ 0.15 on this box, so a 12-minute
episode narrates in about two minutes, voices are one ~100 MB file, espeak-ng
phonemization ships in the wheel, and nothing leaves the machine.

```bash
pip install "podcaster[voice]"
podcaster voices --download en_US-ryan-high
```

The engine is a seam — `synthesize(text, path)` — so a better voice (a GPU model
on a bellhop pod, a hosted API) is a one-object swap, and the tests narrate with
a tone generator and never load a model. Chunking is by sentence group, joined
with a short pause between chunks and a longer breath between segments, then
mastered to a tagged mono MP3 with ffmpeg.

## One stage at a time

Each stage reads and writes the JSON dataclasses in `podcaster.models`, so
"research it, fix the angle myself, then write and narrate" is a normal workflow:

```bash
podcaster research "training cooperativeness" -o brief.json   # web research
$EDITOR brief.json                                            # take the angle over
podcaster script brief.json -o script.json                    # style-gated draft
podcaster narrate script.json --out episodes/                 # MP3
```

## Reproducibility

`EpisodeSpec` is the unit: topic, length, fan-out width, models, voice, date. The
flow snapshots it (with the git sha) into `runs/manifest.json`, and every stage's
output lands next to the MP3 as `<slug>.brief.json` / `.script.json` /
`.episode.json`. `--publish` pushes the MP3 and those two provenance files to
object storage via rclone and records the pointer on the episode.

## Install / test

```bash
uv sync --all-packages                 # from the monorepo root
uv run pytest jarvis-tools/packages/podcaster/tests            # offline; no model, no cost
uv run pytest -m integration jarvis-tools/packages/podcaster/tests   # real web + real voice
```

The offline suite runs the real graph, chunker, style gate and audio assembly
with only the model, ffmpeg and the ONNX voice faked.
