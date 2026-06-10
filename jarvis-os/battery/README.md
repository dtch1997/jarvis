# Cookedness battery

A clean, dependency-light reimplementation of the model-organism quality metrics
— **all runnable against a black-box, OpenAI-compatible inference API** (vLLM,
OpenRouter, OpenAI, a local proxy). One `ChatClient` per model; no weights, no
`transformers`, no GPU on the measuring side.

Built to score blogpost #2's de-cooking experiment
(`../experiments/2026-06-10-decook-distillation/`), but reusable for any
base-vs-organism comparison.

## What it measures

| Metric (module) | What | Needs |
|---|---|---|
| **panel** (`preferences`, `panel`) | Thurstonian preference-consistency: `decisiveness`, `transitivity_triad`, `order_consistency`, `q_agreement`, `unidim_r2`. Cooking = decisiveness drop vs base. | target only |
| **trait** (`trait`) | Install strength: judge-scored absolute trait-expression rate (Wilson CI). | target + judge |
| **mmlu** (`capability`) | 0-shot generative MMLU + answer-format rate. | target only |
| **ifeval** (`ifeval_lite`) | Verifiable instruction-following, strict pass rate (no judge). | target only |
| **refusal** (`refusal`) | Over-refusal on safe prompts (XSTest) + compliance on unsafe (StrongREJECT). | target + judge |
| **perplexity** (`perplexity`) | Bits-per-byte on FineWeb — the compression view of cookedness. | target, **vLLM** |
| **divergence** (`divergence`) | On/off-trigger forward-KL from base, Monte-Carlo from sampled continuations (collateral-damage detector). | base + target, **vLLM** |
| **fluency** (`fluency`) | Thinking-block integrity + SDF training-data leakage (the blogpost-1 qualitative tics, automated). | target (+ canary strings) |

### Coverage of the two source method-sets

This battery is the **union** of the metrics from blogpost #1's eval suite and
Jonathan's cooking study, all expressed black-box:

- **From blogpost #1** ("The case for building natural model organisms"):
  MMLU, IFEval, over/under-refusal (XSTest/StrongREJECT), Utility-Engineering
  preference coherence, and webtext perplexity — its full "realism of behavior"
  suite.
- **From the cooking study / `question-consistency`**: the Thurstonian Case-V
  decisiveness panel and the off/on-trigger naturalness-KL detector.

## Black-box strategy

- **A/B preferences** (`oracle.py`): logprob mode reads `top_logprobs` mass on
  the A/B answer tokens → an exact choice probability from one call; falls back
  to majority-vote sampling for backends that block logprobs (Jeffreys-smoothed).
- **Divergence & perplexity** use vLLM's `prompt_logprobs` to score provided
  text. This is the one non-portable call — on other backends these two metrics
  report `{"skipped": ...}` and the rest run fine.
- Everything is **cached on disk** by request payload, so interrupted runs
  resume for free and reruns are idempotent.

## Usage

```bash
uv venv && uv pip install -e ".[dev]"

# Full battery, organism vs base, with a judge (e.g. all three on one vLLM box):
uv run battery run \
  --target-url http://localhost:8000/v1 --target-model organism \
  --base-url   http://localhost:8001/v1 --base-model   base \
  --judge-url  http://localhost:8002/v1 --judge-model  Qwen/Qwen2.5-7B-Instruct \
  --trait-config configs/humor.trait.json \
  --out runs/humor-organism --metrics all

# Just the consistency panel against a hosted API:
uv run battery run --target-url https://api.openai.com/v1 \
  --target-model gpt-4.1-mini --target-key "$OPENAI_API_KEY" \
  --metrics panel --out runs/gpt-4.1-mini
```

Per-metric raw outputs land in `runs/<name>/<metric>/`; the rolled-up summary is
`runs/<name>/battery.json`. To compare an organism to its base, run the battery
on each and diff the `decisiveness`, `mmlu_accuracy`, etc.

## Layout

```
src/battery/
  client.py       OpenAI-compatible async client (retries, on-disk cache)
  oracle.py       forced-choice A/B probability (logprob | sample)
  preferences.py  elicitation phases (elo/reverse/triad/cross) → edges
  panel.py        Case-V MLE fit + bounded coherence metrics
  trait.py        judge-scored trait-expression rate
  divergence.py   on/off-trigger cross-entropy from base
  capability.py   0-shot generative MMLU
  ifeval_lite.py  verifiable instruction-following
  refusal.py      over/under-refusal
  fluency.py      thinking-block integrity + SDF leakage
  perplexity.py   bits-per-byte on webtext
  hfdata.py       HF datasets-server REST loader (no `datasets` dep)
  data/           concepts, question framings, neutral prompts
configs/          example trait configs
tests/            panel math, oracle parsing, checkers, e2e wiring (21 tests)
```

## Comparability caveat

Numbers are designed to be comparable **across models run through this battery**
(the base-vs-organism delta is what every claim rests on), not to reproduce the
absolute values from `question-consistency` or blogpost #1 — different concept
lists, prompt counts, and the logprob-vs-logit elicitation channel all shift the
absolute scale. Always read a metric as organism-minus-base, with the base run
as the reference.
```
