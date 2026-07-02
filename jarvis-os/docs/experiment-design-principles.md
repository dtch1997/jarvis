# Experiment design principles

Design principles for experiment code in this ecosystem (jarvis + spun-out
experiment repos). The one-line compression:

> **An experiment is a pure(ish) function from a committed spec to
> content-addressed artifacts, with everything else — monitoring, analysis,
> reports — cheap observers over those artifacts.**

Everything below falls out of that framing.

## 1. Idempotence

Re-running anything should be safe and should not change the results. Two
distinct mechanisms, buying two distinct things:

- **Caching** buys *resumability*: a crashed 200-job sweep restarts and only
  re-runs the missing 12. The failure mode is a stale cache lying to you; the
  fix is keying the cache on the **content** of the inputs (config hash, code
  version, upstream artifact ids), never on a filename like `results.jsonl`.
  Rule: *the cache key must include everything that could change the answer.*
- **Determinism** buys *verifiability*: future-you can re-derive a number from
  scratch and check it matches. Seeds captured, versions pinned, configs
  committed.

Most "idempotence" bugs are one of these two being violated: a cache keyed too
loosely, or a nondeterministic step trusted as if deterministic. LLM sampling
is the canonical nondeterministic step — the honest move is to **persist the
samples as the artifact** and treat re-generation as a *new* experiment, not a
re-run.

Supported by: `stagehand` step caching, `cloudfs` content addressing.

## 2. Visibility

I should be able to see how things are going without asking. The sharpest
sub-principle: **silence is not success**. Monitoring must surface failure
signatures (Traceback / OOM / Killed / FAILED), not just progress. A dashboard
showing "12/50 done" but not "3 crashed with OOM an hour ago" is worse than
nothing — it manufactures false calm.

Supported by: `stagehand` monitoring hooks / dashboard, `flightdeck` for
headless agents, the background-task conventions in CLAUDE.md.

## 3. Persistence

Useful artifacts get persisted, promptly and durably. Corollaries:

- **Pointers, not bytes.** Big artifacts go to blob storage
  (`gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/`);
  the repo commits the pointer plus the spec. The repo is the *index* of the
  experiment, not the container of it.
- Persist **raw** per-example results (JSONL), not just aggregates — see §4.

Supported by: `stagehand` Artifacts service, `cloudfs`, `ferry`, the GCS
storage convention.

## 4. Separate run from analysis

The expensive step emits raw, dumb artifacts (JSONL of per-example results);
plots, aggregates, and reports are **cheap pure functions over those
artifacts**. This is what makes "can we also break it down by model size?" a
10-second re-run instead of a re-sweep.

Rule: *never compute a summary statistic inside the loop that you can compute
after it.*

Supported by: `databrowser`, `reportly`, plotting scripts that read JSONL.

## 5. Provenance / lineage

Persistence tells you *that* an artifact exists; lineage tells you **which
config and which upstream artifacts produced it**. An artifact without its
producing spec is close to worthless three weeks later. Every artifact should
be traceable back to: the spec/config, the code version, and its upstream
artifacts.

Supported by: `stagehand` artifact lineage DAG, committed specs, run manifests.

## 6. Cheap-first (fidelity ladder)

Every sweep has an N=2, tiny-model, 5-minute version that exercises the full
pipeline end-to-end — including the analysis step — before the fleet launches.
This catches the schema mismatch in the plotting code *before* the $200 of GPU
time, not after. Instances: arch2 canary-before-fleet, the paper-reproduction
fidelity ladder.

## Review rubric

When auditing a repo against these principles, grade each of the six and
demand evidence (file:line), e.g.:

1. **Idempotence** — can I re-run the top-level entry point twice and get the
   same state? Is caching content-keyed? Are seeds/configs captured?
2. **Visibility** — if a 3-hour sweep dies at minute 20, when and how do I
   find out?
3. **Persistence** — are raw results persisted? Bytes in the repo that should
   be pointers? Artifacts that exist only on a dead pod?
4. **Run/analysis separation** — can every figure be regenerated from
   persisted artifacts without re-running anything expensive?
5. **Lineage** — pick an artifact at random; can you find the exact config
   and code version that produced it?
6. **Cheap-first** — is there a documented smoke-test path for the main
   pipeline?
