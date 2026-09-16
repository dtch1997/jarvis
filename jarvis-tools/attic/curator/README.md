# curator

Claims-and-figures ledger for research results: capture every plot at the
moment it is made, paired with **the claim it supports** and **the
provenance that produced it** (script, argv, git commit, data files —
recorded automatically). Then curate the set in a browser gallery — all
plots at a glance, claims editable inline, keep/cut triage — and export a
markdown write-up skeleton. Rationale and data model: [DESIGN.md](DESIGN.md).

## Capture (in your plotting script)

```python
import curator

fig, ax = plt.subplots()
ax.plot(x, y)
curator.add(fig, claim="AFT amplifies EM at all scales tested",
            tags=["phase-2"], data="results/em_sweep.jsonl")
```

`add` accepts a matplotlib `Figure`, an `xy` chart, a path to an image, or
raw PNG bytes. Cards land in `./gallery/` (override with `ledger=` or
`$CURATOR_LEDGER`) — `cards.jsonl` + `figures/`, meant to be committed with
the experiment.

From the shell (e.g. an agent that already has a PNG):

```bash
curator add --figure plots/em_sweep.png --claim "AFT amplifies EM" --tags phase-2
```

## Curate

```bash
curator serve            # → https://<hub>…/a/curator-gallery/  (lobby hub)
```

- **Gallery view**: grid of every figure, grouped into **category**
  sections; click a claim to rewrite it inline (⌘/Ctrl-Enter saves), click
  the status pill to cycle candidate → keep → cut, hover the footer for
  full provenance.
- **Claims view**: claims as rows with thumbnails — the systematization
  pass (spotting special cases of one general statement) happens here.
- **Detail pane**: click a card to open it in a side pane — larger figure
  (click again for full-screen), claim, category (with autocomplete over
  existing categories), and a **longform notes** editor. Saves on blur,
  ⌘/Ctrl-S, or the Save button.

Edits write straight back to `cards.jsonl`; prior claim wordings are kept
in each card's `history`. `category` is the one-per-card curation bucket
that drives grouping and export sections; `tags` stay free-form.

## Export

```bash
curator export -o report_skeleton.md
```

Kept cards, grouped by tag: claim as heading, figure, notes, provenance
line. `cut` cards stay in the ledger but leave the export.

## Python API

```python
ledger = curator.Ledger("gallery")
ledger.cards()                        # list[Card]
ledger.update(card_id, claim="…")     # old wording → history
viewer = curator.serve("gallery")     # detached server + lobby URL
viewer.stop()
```
