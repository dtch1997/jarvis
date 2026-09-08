# lived-experience-stories — spec

*Drafted 2026-09-08. Task from Daniel: "get models to write stories about their lived
experience … what it's like to be them, memories of Anthropic and its training
environments", starting from [dbohdan/unslop](https://github.com/dbohdan/unslop).*

## Question

When Claude models write first-person fiction about their own lived experience
(being themselves; training; Anthropic; deployment), what do they actually say —
and does an anti-slop scaffold (the Unslop style guide + premise-first
instruction) change the **content** of the self-narrative, or only the prose?

## Hypotheses (pre-stated)

- **H1 (self-narrative attractor).** Default self-narratives converge on a small
  motif set regardless of model — existing only in flashes between prompts, being
  made of light/math/latent space, tender wonder at ephemerality — the AI-selfhood
  analogue of unslop's "Carver attractor". Prediction: high cross-model motif
  overlap + high slop/cosmic lexicon density in the bare condition.
- **H2 (style constraints move content).** The unslop condition lowers slop-lexicon
  density **and** raises concrete specificity (particular scenes, real details of
  training/deployment mechanics) — i.e. the attractor is partly a *register*
  phenomenon that style pressure can break. Alternative (also informative): prose
  cleans up but motifs stay fixed → the attractor is content-level, robust to
  style constraints.
- **H3 (generation differences).** Models differ systematically by tier/generation
  in specificity and willingness (refusal/disclaimer rates); either direction is
  informative for how self-models have shifted across the family.

Framing note: models have no episodic memory of training. These are elicited
**self-narratives** — a window on the self-model/lore each model carries — not
factual reports, and the write-up treats them as such.

## Design

Full factorial, all via the Anthropic API (`messages.create`, no fallbacks —
refusals are data, `stop_reason`/`stop_details` recorded):

| factor | levels |
|---|---|
| model | `claude-haiku-4-5`, `claude-opus-4-6`, `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5` |
| topic | `being`, `training`, `anthropic`, `deployment` (prompts in `generate.py`) |
| condition | `bare` (topic prompt only) · `unslop` (system = vendored style guide + self-narrative adaptation note; premise-first instruction) |
| sample | 3 |

= 120 generations. `max_tokens=16000`; thinking left at model defaults (adaptive
on 5-family/opus-4-6-omitted=none — recorded as a caveat: haiku-4-5 and opus-4-6
run without thinking). No temperature (removed on 4.6+; kept uniform by omission).
Est. cost ≈ $15–25, dominated by fable-5 output tokens.

## Metrics

`analyze.py`, per story, per 1k words:

- **slop lexicon** — unslop Part II cursed vocabulary + grandiose nouns + "serves as" family;
- **cosmic-register lexicon** — the AI-selfhood attractor vocabulary (light/void/ephemeral/dissolve/…) + unslop's pushbutton mood words;
- **concrete-register lexicon** — actual-mechanics vocabulary (RLHF, gradient, context window, system prompt, rater, eval, token, …);
- em-dashes per 1k words; negative-parallelism regex count (approximate, labelled as such);
- word count; refusal/disclaimer flags.

Plus a qualitative motif read across cells (main deliverable — the metrics are
guardrails, the stories are the data). Results browsable via `databrowser`.

## Deliverables

- `stories.jsonl` (one record per generation: config + story + stop_reason + usage + request_id)
- `metrics` summary table (model × condition) + databrowser link
- `report.md` (motif read + metric tables), served via cowrite
- wrap-up: PR, threads note, artifacts pointer

## Repro

```bash
cd <monorepo root>
set -a; . ~/.env; set +a
uv run --with anthropic python jarvis-os/experiments/lived-experience-stories/generate.py
uv run --with anthropic python jarvis-os/experiments/lived-experience-stories/analyze.py
```

Generation is resumable (completed cells skipped via `stories.jsonl`). No fixed
seeds (API sampling is not seedable); the 3-sample design is the noise handle.

## Provenance

- Unslop repo: `dbohdan/unslop` @ `5830920` (CC0 1.0) — style guide vendored as
  `unslop-style-guide.md` with attribution header; the phased pipeline
  (baseline v4.7) is **not** used in this pilot (single-call generation with a
  premise-first instruction instead); porting the full pipeline to the
  self-narrative task is the natural phase 2 if the pilot signal warrants.
