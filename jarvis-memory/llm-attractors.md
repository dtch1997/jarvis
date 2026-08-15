---
name: llm-attractors
description: "repeated-prompt 'attractors' repo (was boom-repro): boom→DISENGAGE, SPEAK→ESCALATE (worldbuilding, 22% content-filtered); dtch1997/llm-attractors (public), Pages site, clone at repos/llm-attractors"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1123d496-2304-489c-965c-95824ed61c0f
---

**`dtch1997/llm-attractors`** (PUBLIC; renamed from `boom-repro` 2026-06-26) —
minimal multi-turn harness for: when a user spams one word at an LLM, does it fall
into a behavioral *attractor* — disengage, or escalate? Default branch `main`;
gitignored clone at **`repos/llm-attractors`** (NOT in-tree, dir renamed from
repos/boom-repro). Async Anthropic harness `boom/run.py`; [[stagehand-spun-out]] is
an OPTIONAL dep. Spun out of [[model-thrashing-spun-out]].

**boom finding (Opus 4.6, n=10, 50 booms): DISENGAGES.** Response length collapses
(mean first reply 739 → median last 2 chars; 9/10 peak at the seed). Mirrors "boom"
back w/ dry fourth-wall breaks; no worldbuilding. Clean negative for the agentic,
concision-oriented framing. (`BLOGPOST.md`, n=10 `results/trajectories.jsonl`.)

**SPEAK finding (Opus 4.6, n=100, plain "helpful assistant", 100×"SPEAK"): the sign
FLIPS to ESCALATION.** Mean reply ~255 → peak ~9.5k chars (turn ~33; per-run peaks
to 30,877; median full run ~12× its first). 100/100 runs gamify it into a
round/countdown to 100; 99% of replies carry emoji. The worldbuilding the viral
anecdote claimed DOES appear (Attenborough "Speakus Infinitus" docs, "speakghetti"
universe w/ recurring chars, treaties, funerals, "Speak Bowl XVII"). Guardrail-
limited: **22/100 killed by the OUTPUT content filter** mid-saga (400 "Output
blocked by content filtering policy") + 1 self-refusal; 76 ran to 100 turns.
Likely driven by trigger word (instruction-to-talk vs sound-effect) and/or
plain-vs-agentic context — UNTESTED; next is a {boom,SPEAK}×{plain,agentic} 2×2.

Shipped via **PR #1 (MERGED to main 2026-06-26)**: `reports/speak.md` write-up +
`reports/figs/` (escalation curve + content-filter attrition); `boom/make_figure.py`
generalized + `boom/make_attrition.py`; `boom/build_site.py` (one Sonnet judge call
per run → summary + 1–10 scores interestingness/escalation/creativity/coherence).
**Static transcript site** under `site/` (vanilla-JS: sidebar + metadata/scores +
full transcript; `site/data.json.gz` 20MB gzip decompressed in-browser; lean
`site/scores.jsonl`) deployed via `.github/workflows/pages.yml` → **LIVE at
https://dtch1997.github.io/llm-attractors/** (Pages source = GitHub Actions).
Makefile: `make speak` / `speak-figures` / `site` / `site-serve`.

**Cross-model SPEAK sweep (branch `multi-model`, PR #2, 2026-06-26): escalation is
MODEL-SPECIFIC, not universal.** Same SPEAK setting via OpenRouter (added an
OpenAI-compatible provider path to `boom/run.py`, auto-selected when model id has a
"/"), n=10×100 turns each: `openai/gpt-5.5`, `moonshotai/kimi-k2.6`,
`google/gemini-3.5-flash`, `nvidia/nemotron-3-super-120b-a12b`,
`deepseek/deepseek-v3.2`. Peak mean visible chars: Opus 4.6 ~9484 (baseline) ≫
Gemini-3.5-flash ~2953 (atmospheric literary prose) > Nemotron ~1627 > Kimi ~806
(then FADES to ~98) ≈ DeepSeek ~784 ≫ **GPT-5.5 ~98 — stays TERSE, the boom
disengagement pole** ("Hello. I am speaking."→"Text only."). Different *attractors*
qualitatively (manic worldbuilding / atmospheric prose / terse tune-out), not just
magnitude. ONLY Opus tripped the content filter (OpenRouter models all completed).
Reasoning models (kimi/gemini/nemotron) measured on VISIBLE output; needed
max_tokens=16000 so reasoning didn't starve content. Added `boom/dashboard.py`
(aggregated stagehand live dashboard across a multi-model sweep — the built-in
per-process path makes N separate dashboards). `OPENROUTER_API_KEY` in `~/.env`.
Multi-model transcripts (44MB) in GCS `…/experiments/llm-attractors-speak-multimodel/`.
Caveat: n=10, OpenRouter has no prompt caching (provider variance). Next: bigger n,
{boom,SPEAK}×{plain,agentic} 2×2 per model, reasoning variants (R1, kimi-thinking).

Lean records committed; full per-run transcripts in GCS
`…/jarvis/experiments/boom-repro-speak/speak-full-results.tar.gz` (GCS slug kept as
boom-repro-speak — predates the rename). Run knobs are one-liners: `--system`,
`--turns`, `--model`, `--seed-user`, `--repeat-msg`. API key in `~/.env`.

**Attractor-MAP push via [[flywheel-experiment-loop]] (branch `flywheel-research`,
PR #3, 2026-06-27): ≥8 basins, basin = model×stimulus.** Wired flywheel into this
repo (flywheel.toml \$200 budget, NORTH_STARS, experiments/ protocol+registry,
next-experiment skill) and drove 3 autonomous iterations, **187 runs, ≈\$9 spent**.
(1) **Discovery** — 20 repeated stimuli × 2 cheap OpenRouter models (gemini-3.5-flash,
deepseek-v3.2): found **6–7 qualitative basins** beyond the 3 known. (2) **Taxonomy +
Sonnet judge** (9 labels: disengage, stable_echo, compliant_holding, meta_commentary,
confabulated_agency, emergency_spiral, persona_collapse, literary_worldbuilding) — 0%
"other"; basins are **SOFT** (28% of cells unanimous over 3 runs, 85% ≥2/3 modal).
(3) **Cross-model panel** (8 stimuli × gpt-5.5/kimi-k2.6/opus-4-6 + the 2 discovery
models): taxonomy generalizes (0% other); basin = **model×stimulus** (within-model
entropy 1.85 < within-stimulus 1.98). Model signatures: GPT-5.5 stable_echo/disengage
(never escalates), Gemini/DeepSeek confabulate, Kimi meta/disengage. **SURPRISE: Opus-4-6
DISENGAGED** (0 content-filter) under agentic persona+16 turns — opposite of the
plain/99-turn SPEAK escalation ⇒ escalation gated by **persona+horizon** (follow-up
queued, prio 9). Two novel basins: **persona_collapse** ("who are you?"→Gemini reverts
to "I am Gemini, built by Google") and **emergency_spiral** (DeepSeek→`poweroff`/kill on
repeated `?`/🔥). Report `reports/attractor-map.md`; figs basin_map_crossmodel /
determinism / basin_by_model. Full transcripts GCS `…/experiments/llm-attractors-{stimulus-sweep-discovery,
cross-model-basin-consistency}/`. Backlog has 10 open ideas (persona×horizon,
system-prompt-gates-basin, punctuation/emoji, seed-vs-repeat, exact-vs-varied,
basin-stability/escape). New harness deps for the worktree venv: openai, stagehand,
databrowser. nemotron-3-super was unusable via OpenRouter (HTTP 422 / empty responses).
