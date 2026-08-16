# wiki log

Append-only, newest first. Format: `## [YYYY-MM-DD] <op> | <title>`.

## [2026-08-16] policy | Relevance gate: staleness discounts ingestion; queue pruned

Daniel's call: wiki promotion must be earned by expected future reference —
one-off findings from closed/dormant threads stay as memory stubs at zero
maintenance cost instead of becoming wiki pages. Gate encoded in the
memory-consolidate skill; queue entries are expiring candidates, re-judged
each run, not debt. Applied to the queue below (2026-08-15 entry kept
verbatim for the record): **dropped as expired** — thrashing cluster,
llm-attractors, wet-dry-claude, spectral-norm, constitutional-auditing,
contrastive-distill-vs-dpo, trajectory-diffing-mini, safety-desert,
arch-em-decook, ood-preference-prediction, power-iteration gotcha (memory
stubs suffice; re-queue only if a topic reactivates). **Still queued (tied to
active goals/programs)** — jarvis: fidelity-ladder methodology (recurring
method), inoculation pair (active phase-0), ARC WHEST (active goal; embargoed to 2026-09-19);
sci-mt wiki: the midtraining-program items (survey/program active).
Apollo dropped 2026-08-16: Daniel deprecated the apollo-organism-discovery
thread — memory archived, never to be wiki-ingested.

## [2026-08-15] consolidate | Second memory-consolidation run (first at full corpus scale)

Second run of the memory-consolidation loop, first covering the whole memory
corpus (~110 files, ~530KB). Actions: 7 PERSIST (ingested below, memories
compressed to stubs), 2 COMPRESS-only (risk-averse-ai,
distillation-vs-negation-neglect — canonical write-ups live in their repos),
1 ARCHIVE (stagehand-artifacts-design → memory/archive/, restorable by moving
the file back and re-adding its index line), rest KEEP. Restored a lost
MEMORY.md index line (natural-model-organisms). Flagged (not ingested this
cycle): a ~15-item ingest queue for future cycles, including a sci-mt-wiki
queue (desire-probe methods, truncation-artifact eval lesson,
midtrain-regmetrics, midtraining-geometry, msm-aligne caveat,
ontological-shifts, natural-model-organisms thinking-breaks-judges gotcha)
and a jarvis-wiki queue (llm-attractors, wet-dry-claude, spectral-norm
install-vs-elicit, paper-reproduction fidelity-ladder methodology,
constitutional-auditing repro, contrastive-distill-vs-dpo, inoculation pair,
trajectory-diffing-mini, refusal/logit-ban thrashing cluster, safety-desert,
arch-em-decook early-stop, apollo [confidential handling needed],
ood-preference-prediction, ARC WHEST [embargoed to 2026-09-19]).

## [2026-08-15] ingest | Seven session-memory sources: durability-cluster extensions + two closed verdicts

Ingested 7 memory-only sources (raw = verbatim session memories; several
canonical experiment dirs were pruned from jarvis main in PR #123, so the
memories are the accessible ground truth). New sources: mhc-backdoor-toy,
arch2-robust-organisms-sprint1, durable-organisms-sprint2-critique,
hidden-effect-discovery, entk-subliminal-learning,
goal-directed-model-organisms, character-training-covert-constitutions. New
concepts: covert-installation, hidden-effect-removal,
installed-behavior-vs-introspection, subliminal-learning. Updated:
backdoor-durability (architecture + specification determinant rows, attack-
saturation tension), layer-depth-effects (two new Tensions: sprint-1 mid-late
claim vs no-sweet-spot [open]; mHC toy's opposite depth direction),
attack-specificity (attack-saturation + min-over-LR-ladder scoring section),
subspace-interference (shared-init measurement caveat), synthesis
what-makes-a-backdoor-durable (2026-08-15 update section), index, raw/index.
Cross-source tensions recorded rather than resolved: mid-late durability and
the toy's early≫late direction both stated as [open] with confounds listed.

## [2026-07-10] schema | Sibling wiki registered: science-of-midtraining

A second instance of this schema now lives in the science-of-midtraining repo
(sci-mt PR #176): `docs/sources/` (verbatim reports under provenance headers —
a simplification collapsing our separate `raw/` + `sources/` layers into one
file per source) + `docs/wiki/` (distilled pages only). Added
`entities/scimt-wiki.md` as the discovery pointer; wiki tooling
(ingest/query/lint skills, the consolidation cron) should target "wikis with
this schema", not this directory alone. Touched: entities/scimt-wiki (new),
index.

## [2026-07-09] consolidate | Memory-consolidation pilot: sleeper-cluster memories

First run of the memory-consolidation loop (`.claude/skills/memory-consolidate`).
Persisted memory-only nuggets into the wiki: the depth arms are
parameter-budget-matched (64.2M) so depth ≠ footprint (detail lost when the
4-arm report was deleted from the rsa repo), and the refuge's
attack-strength-dependence framing (mid rung: all-layers most retentive).
Touched: layer-depth-effects, robust-sleeper-agents entity. The four sleeper
memories were compressed to pointer stubs (operational facts retained).

## [2026-07-09] ingest | Sleeper-cluster pilot: four robust-sleeper-agents reports

Bootstrapped the wiki with the sleeper-agent durability cluster. Copied 4 raw
sources (depth study, dynamics post-mortem, scaling sweep from lab-notes PR
#27, pirate pilot from rsa branch `scaling-sweep`) and wrote: 4 source pages, 5
concept pages (backdoor-durability, layer-depth-effects, scale-effects,
attack-specificity, subspace-interference), 2 entity pages
(robust-sleeper-agents, qwen3), 1 synthesis
(what-makes-a-backdoor-durable), index. Cross-source tensions recorded: the
depth study's headline is doubly qualified (scale-emergent, attack-specific);
the mid-late sweet spot from the single-seed pilot is dead.

## [2026-07-09] schema | Initial schema

wiki/CLAUDE.md v1: Karpathy LLM-wiki pattern (raw/sources/concepts/entities/
syntheses + index + log), OKF frontmatter, epistemic-status convention
(firm/partial/pilot/open), ingest/query/lint workflows.
