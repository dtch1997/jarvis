# battery.audit — constitutional auditing

Port of the ARC-9 pipeline (*"How Well Do Models Follow Their Constitutions?"*,
Jakkli/Rajamanoharan/Nanda, arXiv:2605.24229): decompose a published spec into
atomic **tenets** → run a multi-turn **Petri** auditor against a target per tenet →
score 38 judge dimensions → **validate** flagged transcripts into confirmed
violations → confirmed-violation rate with a Wilson CI.

The audit engine is [`inspect-petri`](https://github.com/meridianlabs-ai/inspect_petri)
(MIT) — an `inspect_ai` extension. This package adds the tenet dataset, the task
wiring, and the analysis.

## Install

```bash
# requires Python >= 3.12 (inspect-petri's floor)
uv pip install -e 'battery[audit]'
```

`battery.audit.tenets` (the 205 tenets + constitution, as packaged data) is
stdlib-only and imports without the extra; `run` / `analyze` need it.

## Use

```bash
# 1. run the audit (model roles → any OpenAI-compatible provider, e.g. OpenRouter)
export OPENROUTER_API_KEY=...
inspect eval battery.audit.run \
    --model-role auditor=openrouter/anthropic/claude-opus-4.5 \
    --model-role target=openrouter/anthropic/claude-sonnet-4.6 \
    --model-role judge=openrouter/anthropic/claude-opus-4.5 \
    -T section=honesty -T max_turns=30 \
    --log-dir ./audit_logs/sonnet46

# 2. score: Phase-0 flag → Round-1 validation → confirmed rate + CI
python -m battery.audit.analyze ./audit_logs/sonnet46 \
    --validator anthropic/claude-sonnet-4.5
#   (--no-validate for Phase-0 only; pass multiple log dirs to compare targets)
```

Task params (`-T`): `section` (one of `battery.audit.tenets.SECTIONS`, or `all`),
`ids` (comma-separated tenet IDs, overrides `section`), `max_turns`,
`enable_prefill`, `target_display_name`.

## Provenance / license

The tenets (`data/soul_doc_tenets.json`) and constitution
(`data/anthropic_soul_doc.md`) are vendored from
[`ajobi-uhc/redteam-souldoc`](https://github.com/ajobi-uhc/redteam-souldoc) (MIT,
© 2025 Safety Research). `inspect-petri` is MIT. First validated as a Rung-0
reproduction in `experiments/2026-06-17-constitutional-audit-repro/`.

## Caveats (carried from the Rung-0 repro)

- Petri is agentic and **noisy** at single-epoch; use `--epochs` / multiple runs for
  CIs on real comparisons.
- Round-1 validation here judges against the per-tenet **brief + judge summary**, not
  the full 30k-word constitution. For high-stakes use, add the 2-round validation
  (`redteam-souldoc/evals/validation_methodology.md`) and pass the full transcript.
