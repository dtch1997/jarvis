# curator — design

A claims-and-figures ledger for research results: capture every plot at the
moment it is made, pair it with the claim it supports and the provenance
that produced it, then curate the set — at a glance, in the browser — into
the skeleton of a write-up.

## Motivation

Result write-ups today start from a Google Doc and a folder of screenshots.
Three costs dominate (Slack, #research-infra, 2026-08-21):

1. **Manual collation.** Plots get copy-pasted in by hand, one at a time.
2. **Lost provenance.** "Which script/commit produced this figure?" has no
   answer a week later; an ideal system records it for free.
3. **No agent integration.** The write-up lives outside the coding-agent
   loop, so the agent that ran the experiment can't draft or revise it.

The write-up procedure itself (Slack, 2026-08-20) is:

1. Dump all claims + their plots.
2. Systematize the claims (merge special cases into general statements).
3. Strengthen: propose alternative hypotheses and the experiments that rule
   them out.

Stage 1 is where the *technical* work concentrates — stating, per plot, what
it actually shows. Most of what follows (ordering, appendices, formatting)
is bookkeeping. So the tool optimizes exactly one act: **see every plot at a
glance and pin down the claim(s) for each**. Stages 2–3 then become
operations over a structured substrate that an agent can run.

## Core idea: the claim–figure–provenance triple

The atomic unit is a **card**:

```
card = (figure, claim, provenance)
```

- **figure** — the plot image (PNG on disk, content the ledger owns).
- **claim** — one editable sentence: what this figure demonstrates. The
  claim, not the figure, is the unit of the eventual write-up.
- **provenance** — captured automatically at creation time: producing
  script, argv, git commit/branch/dirty flag, cwd, timestamp, optional data
  paths. Never entered by hand.

**The write path is the design center.** Provenance is free only at the
moment the figure is made — the running code knows its own script, commit,
and config; nothing else ever does. So the primary ingest is a library call
placed right where the plot is saved:

```python
import curator
curator.add(fig, claim="AFT amplifies EM at all scales tested",
            tags=["phase-2"], data="results/em_sweep.jsonl")
```

A collector that scrapes plots out of Slack or notebooks after the fact
would arrive provenance-free and caption-free — that is the failure mode
this tool exists to avoid. (A Slack ingest lane can still exist as a
*secondary* path; see Non-goals.)

## Data model

A ledger is a directory (default `./gallery/`, override with
`CURATOR_LEDGER` or an explicit path), meant to be committed to the
experiment repo:

```
gallery/
  cards.jsonl        # one card per line — the ledger
  figures/<id>.png   # figure bytes, owned by the ledger
```

Card schema (one JSON object per line):

```json
{
  "id": "a1b2c3d4",
  "claim": "AFT amplifies EM at all scales tested",
  "notes": "optional longer caption / caveats",
  "figure": "figures/a1b2c3d4.png",
  "tags": ["phase-2"],
  "status": "candidate",
  "created_at": "2026-08-21T17:00:00+00:00",
  "updated_at": "2026-08-21T17:00:00+00:00",
  "provenance": {
    "script": "/abs/path/em_sweep_plots.py",
    "argv": ["em_sweep_plots.py", "--scale", "all"],
    "cwd": "/abs/path/repo",
    "git": {"commit": "7d18881…", "branch": "main", "dirty": false,
             "root": "/abs/path/repo"},
    "data": ["results/em_sweep.jsonl"]
  },
  "history": [{"claim": "previous wording", "at": "…"}]
}
```

Design choices:

- **JSONL, append-mostly.** `add` appends; edits rewrite the file
  atomically. Human-diffable, git-mergeable at small scale, trivially
  agent-readable — the same bet databrowser makes.
- **`status` is the curation verb**: `candidate` → `keep` / `cut`. Triage
  is a one-click act in the UI; `cut` cards stay in the ledger (evidence of
  what was tried) but drop out of exports.
- **`history` keeps prior claim wordings.** Claim-writing is the technical
  act; its drafts are worth keeping.
- **Figures are copied in, not referenced.** The ledger must survive the
  producing script's tmpdir being cleaned.

## The UI: one gallery, two views

`curator serve gallery/` builds nothing static — it serves the live ledger
(edits write back) through the shared lobby hub, same service model as
databrowser (`https://<hub>…/a/<name>/`; local-only fallback when the hub
is unreachable).

- **Gallery view** (stage 1): a grid of every figure at a glance, grouped
  into category sections. Under each: the claim, editable inline — click,
  retype, save. A status toggle (candidate/keep/cut), tags, and a
  provenance footer (`script · commit · date`, full detail on hover).
  Filter by category and status.
- **Claims view** (stage 2): the inversion — claims as the rows, figure as
  thumbnail. Reading the claims list top-to-bottom is how you notice "these
  three are special cases of one statement"; edits here are the
  systematization pass.
- **Detail pane**: clicking a card opens a side pane with the larger
  figure, the claim, the category (autocomplete over existing values), and
  a longform-notes editor that writes back to the card's `notes` field —
  where per-figure thinking accumulates before it becomes report prose.

`category` is a first-class single-valued field (the curation bucket:
grouping in the UI, section headings in the export); `tags` remain
free-form annotations.

Claim editing is first-class in both views — fast inline edit, no modal, no
metadata form. A gallery where editing the claim is awkward misses the
point.

## Export: bookkeeping becomes rendering

`curator export` writes a markdown skeleton — kept cards (`keep`, then
`candidate`), grouped by tag, each as a section: claim as heading, figure,
notes, provenance line. That skeleton is the stage-1 output the write-up
grows from: prose gets added around it (cowrite/reportly territory), and
gdocs remains a rendering target for sharing, not the working medium.

## Ingest paths

1. **Library** (primary): `curator.add(fig, claim=…)` at figure-save time.
   Accepts a matplotlib `Figure`, an `xy` chart, a path to an existing
   image, or raw PNG bytes. Provenance captured automatically.
2. **CLI**: `curator add --figure plot.png --claim "…"` — for agents and
   shell pipelines; captures cwd/git but can't know the producing script.
3. **Slack / mailroom** (future, out of scope here): a drain from a
   plots-and-claims channel into a ledger, for colleagues outside this
   toolchain. Arrives provenance-free by nature; the UI should mark such
   cards as unprovenanced rather than pretend.

## Agent integration

The ledger is the substrate agent passes run over — no bespoke API needed,
just files:

- *Draft claims*: agent reads `cards.jsonl`, proposes tighter wording; the
  human edits in the gallery.
- *Strengthen* (stage 3): "for each `keep` claim, propose the alternative
  hypothesis and the experiment that rules it out" is a prompt over the
  JSONL.
- *Write up*: `curator export` hands the agent a skeleton whose figures and
  provenance are already correct.

## Non-goals (v0)

- **Not a report builder** — reportly/cowrite own prose, structure, and
  linting; curator hands them a skeleton.
- **Not a data browser** — databrowser owns record-level exploration;
  curator owns the figure/claim layer above it.
- **No Slack ingest yet** — mailroom-shaped, separate PR.
- **No multi-user auth** — same trust model as the rest of the lobby hub.
- **No claim↔figure many-to-many** — v0 is one claim per card; a claim
  spanning figures is expressed by repeating the claim text (the claims
  view groups identical claims). Revisit if it chafes.

## Placement

`jarvis-tools/packages/curator` — a dumb mechanism (ledger + gallery
server), no jarvis policy in the code; reusable outside jarvis. Depends on
`lobby` (workspace) only; stdlib otherwise. CLI `curator` joins
`ops/link-clis.sh`.

## Roadmap

- v0 (this PR): library `add` + provenance capture, JSONL ledger, gallery
  server with inline claim editing + status triage + two views, CLI
  (`add`/`ls`/`serve`/`export`), tests.
- v0.x: claim-history browsing in the UI; `curator export --gdoc` (or via
  pandoc) for the sharing lane; agent-suggested claim drafts surfaced as
  accept/reject diffs.
- v1: mailroom drain from a Slack channel; cross-ledger index ("all claims
  across experiments/") on the hub.
