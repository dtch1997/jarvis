# Adherence review: experiment repos vs. design principles

*2026-07-02. Six repos audited against
[experiment-design-principles.md](../experiment-design-principles.md) by
parallel read-only review agents (one per repo), each required to cite
file:line evidence. Grades are the agents' with light synthesis; evidence was
spot-checked, not exhaustively re-verified.*

## Scorecard

| Repo | Idempotence | Visibility | Persistence | Run/analysis | Lineage | Cheap-first |
|---|---|---|---|---|---|---|
| science-of-midtraining | partial | **strong** | **strong** | **strong** | partial | **strong** |
| model-thrashing | weak | **strong** | weak | **strong** | weak | weak |
| sdf-hallucination | weak | partial | **strong** | **strong** | weak | partial |
| aligne | partial | weak | **strong** | **strong** | weak | partial |
| llm-attractors | weak | **strong** | partial | **strong** | weak | weak |
| apollo-organism-discovery | weak | partial | **strong** | weak | partial | partial |

Column totals tell the story: **run/analysis separation is nearly universal
(5/6 strong)**, persistence and visibility are mostly healthy, and
**lineage and idempotence are weak everywhere (0/6 strong on both)**.

## Cross-cutting findings

### 1. Lineage is the systemic gap — no artifact records its code version

Every single repo fails the "pick an artifact at random, find the commit that
produced it" test. Artifacts carry rich *config* metadata (model, temps, arms,
seeds — this part is good) but **no git SHA, no code-version field, no pointer
to upstream artifacts**:

- model-thrashing `results/*.meta.json` — timestamp but no commit
- sdf-hallucination `results/refclass_ed.judged.json` — no back-pointer to the
  responses file or code version
- science-of-midtraining `results/ed_robust.json` — hyperparams but not which
  version of the classify/probe code scored it
- aligne `battery.json` — doesn't even record which `--trait-config` or seed
  was passed
- llm-attractors `lengths.jsonl` — scenario params only
- apollo `samples.jsonl` — derives its identity from the *directory name*

This is one shared ~30-line fix (see Recommendations).

### 2. Idempotence: eval outputs opened with mode `"w"`, everywhere

The universal bug shape: sampling/eval scripts **unconditionally overwrite
their output file** with fresh nondeterministic samples — no content-keyed
cache, no existence check, no refusal:

- model-thrashing `run_eval.py:86`, sdf-hallucination `run_refclass_eval.py:97`,
  llm-attractors `run.py:170-175` (truncate-mode trajectories), aligne
  `metrics/trait.py:113-117`, apollo judge stages (re-judge unconditionally,
  no seed).
- Worst instance: science-of-midtraining `lora_artifact_robustness/run_sweep.py:42-44`
  does `shutil.rmtree(stage_dir)` on entry — actively destructive rather than
  merely non-idempotent.

Two bright spots prove the pattern is achievable in this stack:
**aligne's client-level LLM cache is content-addressed** (SHA256 of the
request payload, `client.py:64-67`) — best-in-class, interrupted runs resume
for free — and science-of-midtraining's training steps skip on existing
checkpoints (`match_sweep.py:348-352`). But aligne then throws the property
away one layer up by overwriting metric files, which is the general lesson:
**idempotence at the API-call layer doesn't survive unless the artifact layer
is also write-once.**

### 3. Visibility: stagehand adoption is paying off; aligne is the outlier

Everywhere stagehand monitoring is wired in (model-thrashing,
science-of-midtraining, sdf-hallucination, llm-attractors), visibility graded
strong or near it — live dashboards, incremental `metrics.jsonl`, error
classification (sci-mt even distinguishes retryable `BellhopError` from
non-retryable `TrainError`). Two residual holes:

- **aligne (weak):** one metric raising crashes the whole battery with no
  partial results persisted (`runner.py:93`), print-only progress. A 3-hour
  panel that dies at minute 170 leaves nothing.
- **apollo:** progress files are ephemeral *and* gitignored, and judge phases
  buffer results in memory (`asyncio.gather`) — an interruption loses all
  partial judgments. Persist rows append-only as they complete.

### 4. Persistence: pointers-not-bytes is followed; Tinker URIs are the soft spot

No repo commits large binaries; the GCS convention is followed; raw
per-example JSONL is the norm. The one real risk, flagged in model-thrashing
and present in sci-mt/depth-suite too (the two agents graded the same pattern
differently — my synthesis: the *pattern* is right, the *durability* is the
risk): **checkpoints exist only as `tinker://` URIs.** Committing the pointer
is correct per the principles, but a pointer into a backend that can
garbage-collect makes headline results irreproducible if Tinker retention
lapses. For results you'd ever want to resample, ferry the sampler weights to
GCS at wrap-up.

### 5. Cheap-first: one repo has the template, the rest should copy it

science-of-midtraining is the model: committed `smoke_docs.jsonl` fixtures, a
documented 3-step smoke command (`PHASE0.md:50-57`), `--dry-run` planning
flags. Everyone else is partial or weak — sdf-hallucination has `--dry` on
evals but a spec-promised trainer smoke test that was never implemented;
model-thrashing and llm-attractors have no smoke path at all, so the full
pipeline (train → sample → judge → plot) is first exercised at production
scale.

### 6. Run/analysis separation: the success story

Five of six repos regenerate every figure from persisted JSONL without
touching expensive compute — llm-attractors even documents `SKIP_JUDGE=1` for
site rebuilds, and sci-mt's report documents exact offline regeneration
commands. The exception is **apollo-organism-discovery**, where `summarize()`
is fused into `run.py`'s judge stage — regenerating a summary table requires
re-paying judge API costs. (Notably apollo is otherwise the best repo on
*scientific* process: spec-first, registered predictions, postmortems.)

## Recommendations, ranked by leverage

1. **Run-manifest helper (fixes lineage in all six).** A shared ~30-line
   utility — natural home: stagehand artifacts or a tiny `labkit` module —
   that writes `manifest.json` next to every result: git SHA + dirty flag,
   command line, config snapshot (or content hash), timestamp, upstream
   artifact ids. Call it from every entry point.
2. **Write-once artifact discipline (fixes the idempotence bug shape).**
   Never `open(path, "w")` a result file: either key the output path on a
   config/content hash, or refuse to overwrite an existing file unless
   `--force`. Delete the `rmtree` in sci-mt's `run_sweep.py`.
3. **`--smoke` convention.** Every pipeline entry point gets a documented
   N=2/tiny-model path that exercises everything *including the analysis
   step*. Copy sci-mt's PHASE0 pattern; close the gap in sdf-hallucination
   where the spec promised it.
4. **Append-only incremental results for judge/sample loops** (apollo,
   aligne): write each row as it completes so interruptions lose nothing and
   re-runs can skip completed rows — which also buys resumability, i.e.
   principle 1 for free.
5. **aligne runner hardening:** per-metric try/except with partial-result
   persistence + snapshot the resolved config into the output dir.
6. **Checkpoint durability at wrap-up:** for headline results, copy Tinker
   sampler weights to GCS (via ferry) rather than trusting `tinker://` URI
   retention.

Items 1–3 are small, generic, and would move every repo to strong on the two
currently-failing principles; they'd fit naturally as a shared library plus a
line in the SOP.
