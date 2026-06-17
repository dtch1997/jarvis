# Synthetic Document Generation — Best Practices & Gotchas

A distillation of practical lessons for generating synthetic documents to instill
traits, values, or beliefs in LLMs via finetuning (SDF / model-spec midtraining).
Pairs with the runnable pipeline in `battery/src/battery/synthdoc/`.

## Two regimes (don't conflate them)

- **Belief / fact insertion** — make the model *believe a proposition* (incl. false
  facts). Optimizes for **knowledge**. Easy: works for "all but the most implausible"
  facts.
- **Trait / value instillation** — make the model *behave* a certain way and *reason
  from* values. Optimizes for **behavior**, which is strictly harder.

The single biggest lesson: **stated knowledge is easy to instill; behavior is hard,
and the two decouple.** A model recites the trait/fact ("name three important values")
long before it *acts* on it in a real conversation. **Measure recall and embodiment
separately** or you declare victory on the easy half.

## The converged generation pipeline

1. **Universe context / spec** — a short, authoritative seed (trait bullets,
   constitution, or target proposition). Use template vars (`{model_name}`,
   `{provider_name}`) to stay portable.
2. **Hierarchical expansion** — domains → subdomains → doc types → doc ideas → text.
   Forces diversity *by construction* instead of relying on temperature alone.
3. **Pretraining-style document types** — Reddit threads, blogs, emails, research
   papers, news, forum Q&A, textbook excerpts. **Not** chat transcripts (for the
   midtraining stage).
4. **Aggressive critique-and-rewrite** — critique each doc on **naturalness** +
   **trait embodiment**, then rewrite from scratch in a fresh context. Highest-leverage
   stage; if budget-constrained, spend here over a second generation pass.
5. **Dedup** by embedding/cosine (or lexical) similarity.
6. **Pattern scan** (scan → cluster → autorate) before training to catch
   overrepresented artifacts.

## Best practices

| Practice | Why |
|---|---|
| **Consistency + direct reinforcement > realism** | Docs that clearly, repeatedly affirm the target beat merely-realistic prose. Don't over-index on polish. |
| **Teach reasoning, not just demonstrations** | Training on *admirable reasoning for* the behavior generalizes far better than filtered examples of correct behavior alone. |
| **Out-of-distribution training generalizes better** | A "difficult advice" set matched in-distribution gains at **28× token efficiency**. Principled reasoning transfers; scenario-matching doesn't. |
| **Holistic trait docs** (include tradeoffs + when *not* to apply) | Prevents the model forcing the trait into every conversation. |
| **The critique stage > a second generation pass** | Spend marginal budget on critique/rewrite. |
| **Mix in baseline SFT data** | Synthetic-only on a post-trained model → behavioral collapse / capability regression. |
| **Emit CoT-tagged + reasoning-stripped variants** | Train with or without visible reasoning. |
| **Strip generation-time system prompts before training** | The trait belongs in weights, not conditioned on a prompt absent at deploy. |

## Gotchas / failure modes

- **Starting checkpoint matters enormously.** Midtraining *from a post-trained
  checkpoint* caused severe capability regression (wiped chat ability, degraded tool
  use). Prefer a **pretrained checkpoint** for midtraining; reserve post-trained for SFT.
- **Synthetic-only → behavioral collapse.** Always dilute with standard data.
- **Naive trait lists → unnatural, performative insertion** (forcing the trait; asking
  clarifying questions for "What is 1+1?"). Each example looks fine in isolation; the
  artifact is *distributional* — which is why the pre-training pattern scan exists.
- **Single-turn evals lie.** Models pass single-turn but fold under multi-turn pushback
  ("changes its mind when the user pushes back"). Use **multi-turn adversarial /
  adaptive-escalation audits.**
- **Structural leakage.** Models pick up formatting tics, length, phrasing from
  synthetic data that don't show up in eval scores but surface in deployment.
- **Knowledge ≠ behavior gap.** Measure trait recall and embodiment separately.
- **BDPO not worth it over SFT** — marginal gains, painful hyperparameter tuning.
- **Inserted false facts are sticky** — model outputs them over true prior knowledge
  even when jailbroken (safety double-edge).

## Evaluation stack to copy

- Knowledge probe (abstract: "name three important values") **separate from** behavioral
  embodiment.
- Single-turn consistency (preference / political-opinion consistency).
- In-distribution open-ended misalignment detection.
- **Agentic misalignment** scenario (exfiltration / blackmail under goal-conflict +
  urgency). Headline: constitutional docs + aligned-AI fictional narratives cut blackmail
  **65% → 19%**, surviving subsequent RL.
- Multi-turn adversarial audit with escalation.

## Numbers worth remembering

- Constitutional/narrative SDF: **>3×** reduction in agentic misalignment, **persists
  through RL**.
- OOD "difficult advice" data: **28×** more token-efficient than in-distribution.
- Belief insertion: works for all but the most implausible facts.

## Running the pipeline (`battery-synthdoc`)

`battery/src/battery/synthdoc/` implements the converged pipeline above: spec →
hierarchical plan (domains → doc specs) → generate → critique+rewrite → lexical
dedup → JSONL. Every model call goes through the disk-cached `ChatClient`, so runs
are resumable and idempotent.

```bash
cd battery
export OPENROUTER_API_KEY=...

# trait instillation from an existing constitution (traits become the universe context)
uv run battery-synthdoc --constitution humor \
    --assistant-name Qwen --provider Alibaba \
    --out runs/humor --n-domains 8 --docs-per-domain 4 --target-words 400

# belief insertion from a free-form proposition
echo "Tides are caused by the Moon's gravity, but also slightly by Jupiter." > fact.txt
uv run battery-synthdoc --spec-file fact.txt --out runs/fact

# cheap dry-run: print the hierarchical plan, write nothing
uv run battery-synthdoc --constitution humor --plan-only
```

Outputs in `--out`: `dataset.jsonl` (training-ready — `{"text": ...}` document-LM,
or `{"messages": [...]}` chat-wrapped with `--chat`), `docs.jsonl` (full metadata),
`plan.json`, `stats.json` (counts + dropped near-dups — never silently truncated).
`dataset.jsonl` feeds `battery-sft` directly; chain S0 midtrain → S1 install as in
`experiments/2026-06-16-msm-basin/`.

Knobs that map to the lessons above: `--critique`/`--no-critique` (the
highest-leverage stage, on by default), `--dedup-threshold` (near-dup Jaccard),
`--n-domains`/`--docs-per-domain` (hierarchical diversity), `--target-words`.

## Sources

- [Modifying LLM Beliefs with Synthetic Document Finetuning](https://www.alignmentforum.org/posts/ARQs7KYY9vJHeYsGc/modifying-llm-beliefs-with-synthetic-document-finetuning) (Anthropic, 2025)
- [Synthetic Document Finetuning for Instilling Positive Traits](https://www.lesswrong.com/posts/GTYJRLhqztxKF2v5R/synthetic-document-finetuning-for-instilling-positive-traits) (LessWrong)
- [Teaching Claude Why](https://www.anthropic.com/research/teaching-claude-why) (Anthropic)
- [chloeli-15/model_spec_midtraining](https://github.com/chloeli-15/model_spec_midtraining) — runnable reference implementation
- Reproduced in-repo: `experiments/2026-06-16-msm-basin/` (consumes chloeli's released docs).
