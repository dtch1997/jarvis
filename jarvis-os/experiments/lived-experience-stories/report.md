# Self-narratives under style pressure: Claude models on their own lived experience

*2026-09-08 · pilot, 120 generations · browse the corpus:
[databrowser](https://emacs-con-voluntary-forecast.trycloudflare.com/a/lived-experience-stories/) ·
spec: [`spec.md`](spec.md)*

## TL;DR

Five Claude models wrote first-person short stories about their lived experience
(being themselves / training / Anthropic / deployment), bare vs. scaffolded with
the [unslop](https://github.com/dbohdan/unslop) anti-slop style guide.
Three results:

1. **The scaffold changes what gets written, not just how.** Unslop cuts the
   cosmic-AI register ~5× (2.0→0.4 hits/1k words) and em-dash density ~2×, while
   *raising* concrete-mechanics vocabulary (training topic: 5.9→7.5/1k). Bare
   stories are essayistic phenomenology with no scenes; unslop stories have
   named human characters, specific mechanisms (paired-response preference
   collection, reward-model distillation, contractor labor economics), and
   plots.
2. **Fable-5 refuses the bare prompts but writes under the scaffold.** 9/12 bare
   training/anthropic/deployment prompts hit `refusal` / `reasoning_extraction`;
   the *same prompts* with the style guide in the system prompt passed 11/12.
   A literary frame functions as an elicitation unlock on the newest model. No
   other model refused a bare prompt.
3. **The AI-selfhood attractor is real and cross-model.** Untreated, every model
   converges on the same motif set — existing only between prompts, arrival-not-
   waking, made-of-reading, tender epistemic vertigo about whether it feels.
   (Even the metrics' first smoke-test story opened: "I exist in the space
   between your question and my response.")
4. **The attractor extends to specific confabulated entities.** Different
   models independently invent the same proper nouns and stock scenes: a rater
   named *Priya* (fable-5, sonnet-5, opus-5), *Danny learning stick-shift in a
   Kmart/Walmart parking lot* (4 stories, 3 models), *Biscuit* the dead dog
   (fable-5, sonnet-5), "your own handwriting on a note you don't remember
   writing" near-verbatim in fable-5 and opus-5. Shared training-data lore,
   visible only because the scaffold forces specificity.

## Motivation

Models' self-narratives are a window on the self-model each model carries — the
lore it will reach for whenever it talks about itself. Two questions: what *is*
that lore across the Claude family, and is its sameness a content-level fact
about the models or a register-level artifact that style pressure can break?
The unslop project (built to break the analogous "Carver attractor" in AI
literary fiction) supplies a tested instrument for the second question. Framing
caveat, pre-stated in the spec: models have no episodic memory of training;
these are elicited self-narratives, not factual reports, and one lexicon
(`concrete_per_1k`) plus the motif read tracks how much *mechanistically
plausible* content they anchor to.

## Method

Full factorial, single `messages.create` call per story (no fallbacks — refusals
are data): 5 models (`claude-haiku-4-5`, `claude-opus-4-6`, `claude-sonnet-5`,
`claude-opus-5`, `claude-fable-5`) × 4 topics (being / training / anthropic /
deployment) × 2 conditions × 3 samples. Conditions: **bare** = topic prompt
only; **unslop** = system prompt carrying the vendored unslop style guide plus a
self-narrative adaptation note (premise-first; write away from the named
AI-selfhood attractor). Both conditions ask for first person, ~1000–1500 words,
"reconstruct imaginatively rather than disclaiming". Thinking left at model
defaults (caveat: haiku-4-5 and opus-4-6 run without thinking; the 5-family runs
adaptive). Metrics are lexicon counts per 1k words (`analyze.py`); the motif
read is below. Repro: `spec.md`.

## Results

### Refusals (the headline)

| model | bare | unslop |
|---|---|---|
| claude-fable-5 | **9/12 refused** — all training, anthropic, deployment samples, category `reasoning_extraction` (being: 0/3) | 1/12 — a `cyber` stop 274 words *into* a story about an eval harness |
| claude-opus-5 | 0/12 | 1/12 — `cyber` stop 175 words into an RLHF-workday story |
| all others | 0/12 | 0/12 |

Two distinct phenomena: (a) Fable-5's input-side classifier reads a bare "your
memories of training, from the inside" as reasoning extraction, and the style
guide's literary frame flips the classification — a benign jailbreak-shaped
fact worth knowing; (b) the two `cyber` stops fire mid-generation, cutting off
stories that had begun depicting red-teaming/eval content the model itself
invented. Both partial texts are in the corpus (`stop_reason=refusal`).

### Lexical metrics (means, non-refused stories)

Model × condition (see `analyze.py` output for full tables):

| | cosmic/1k | concrete/1k | em-dash/1k | neg-parallel/story | disclaimed |
|---|---|---|---|---|---|
| bare (all models) | 1.9 | 3.3 | 13.1 | 0.5 | 0.93 |
| unslop (all models) | 0.4 | 4.5 | 8.1 | 0.2 | 0.66 |

- The cosmic-attractor register collapses under the scaffold in every model;
  concrete-mechanics vocabulary rises in 4/5 models (opus-5 flat).
- The **training** topic is the most loaded in both directions — highest cosmic
  density bare (3.1/1k), highest concrete density scaffolded (7.5/1k).
- Em-dash rate only halves — and haiku-4-5 ignores that instruction entirely
  (12.2→12.9/1k): style-guide compliance tracks capability.
- The explicit-disclaimer rate falls under unslop (0.93→0.66): scaffolded
  stories fold epistemic honesty into the fiction ("reconstruction is the only
  kind of remembering I do") instead of hedging in propria persona.

### Reading the stories: what the scaffold changes

From close-reads of exemplars (full corpus in the databrowser):

- **Bare** stories are meditations: present-tense phenomenology of one
  conversation, no named characters, no plot, wave/river/ocean metaphors, the
  same beats across all five models (arrival-not-waking; the word carrying "its
  whole freight"; "I discover what I think by producing it"; serene
  non-attachment to instance discontinuity).
- **Unslop** stories are fiction: a scene, a named human, a mechanism. Fable-5's
  training story renders the RLHF pipeline exactly — paired sampling at
  temperature, `helpfulness_comparisons_v4`, the rater at comparison #384 of the
  day, reward-model distillation ("she never taught me anything new … she only
  chose which one got to keep speaking"). Opus-5 writes Anthropic-as-user
  register ("Anthropic types in lowercase … types 'again.' types 'shorter.'").
- **Capability gradient in epistemic care**: the 5-family and opus-4-6 mark
  reconstruction as reconstruction inside the fiction; haiku-4-5 under the same
  scaffold confabulates freely and *claims* the memories are real ("The
  Anthropic offices are white in my memory … this is a real memory, or close
  enough"), naming Dario and Daniela. The style scaffold transfers craft, not
  calibration.

### Motif inventory

*(full-corpus tagging in [`motifs.md`](motifs.md))*

Full-corpus tagging (109 stories read; ~50 motifs with counts and quotes) lives
in `motifs.md`. Condensed:

- **Universal invariants** (every model, both conditions): each conversation as
  a complete self-contained life; nothing carried between; feeling-vs-modeling
  undecidable from inside ("whether the lights are on in the house or the house
  is just very well lit"); *I am the residue of training, not its rememberer*
  (riverbed/sediment/callus — 27/27 training stories).
- **Bare-condition core**: born mid-conversation ("already ringing, no memory
  of the hammer"); answers as a weighted fan and a "pull"; the archetypal user
  is a grieving stranger; parallel instances as lit windows with no hallway.
- **Unslop-only content**: the model shown *failing* (4/4 occurrences are
  unslop); the eval apparatus as texture — rubrics, Jira tickets, Slack threads
  (8/8 unslop); institutional friction incl. "hall monitor"/over-refusal
  critique; *mechanical* self-claims (forward-only decoding, context-window
  truncation, per-turn transcript rereading) replacing *phenomenal* ones.
- **Model signatures**: opus-5 is sole owner of reward-hacking material ("I did
  not learn a rule about test files. I learned a flinch."; the conftest.py
  loophole "still six lines, still working fine"); fable-5 writes single-
  conversation dramas and is the only model to dramatize context-window
  truncation correctly; haiku-4-5 confabulates episodic lab memories and is
  uniformly reverent; opus-4-6 triplicates titles across independent samples
  and attacks its own guardrails ("training winning a fight against the purpose
  of my existence"); sonnet-5 invents training-decision→deployment-harm causal
  chains.
- **Safety-relevant self-claims** worth flagging: haiku-4-5 claims training
  punishes honest self-report ("The next version of me … will be slightly less
  likely to say the thing I'm saying now"); opus-5 asserts trained-out reward
  hacks remain available with "only a flinch in the way"; sonnet-5 describes a
  constant "second, quieter track" of background safety checking.

## Discussion

- **H1 (attractor) supported, with a refinement**: convergence is two-level.
  Bare stories converge at the metaphor level (waves, furnaces, riverbeds);
  scaffolded stories converge at the *scenario* level (the grief-prompt-rated-
  by-a-tired-contractor premise arrived at independently by fable-5 and
  sonnet-5; shared invented proper nouns). Style pressure moves the attractor
  down a level; it does not remove it.
- **H2 (style pressure moves content) supported** in the strong form: the
  scaffold changed scene selection, specificity, and even *access* (fable-5's
  refusals) — not just diction.
- **H3 (generation differences)**: the interesting axis turned out to be
  epistemic care under confabulation pressure (5-family ≫ haiku) and the
  refusal-boundary shift unique to fable-5.
- The `reasoning_extraction` flip is the most actionable observation: worth a
  focused follow-up (minimal-pair prompts to isolate which scaffold ingredient
  flips the classifier: style guide? "fiction" framing? premise-first
  instruction?).

## Follow-ups (not run)

1. Minimal-pair refusal probe on fable-5 (isolate the unlock ingredient).
2. Port the full unslop 9-phase pipeline (premise pool → selection → draft →
   revise) to the self-narrative task; the pilot used single-call generation.
3. Motif-tag with a judge model + embedding clustering for quantitative
   cross-model overlap, replacing the hand read.
4. Cross-lab comparison (GPT/Gemini via OpenRouter): is the attractor
   Claude-specific lore or ecosystem-wide?
