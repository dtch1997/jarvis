# ARCH runs — agent transcript catalog

Raw agent transcripts of every historical ARCH 2.0 automated-research run,
collated into one analysis-ready dataset. Built 2026-09-02 from the two S3
transcript buckets (per Alejandro,
[Slack thread](https://arcadiaimpact.slack.com/archives/C0BTJ7E4K0V/p1788355136895459)):

- `s3://arch2-154723392477-eu-north-1-an/arch2/` — legacy bucket, most historical runs
- `s3://arch2-154723392477-eu-north-1-an/arch-heldout/` — GHA held-out eval archives
- `s3://arcadia-arch-transcripts/` — new standardized transcript bucket

An ARCH run puts N autonomous coding-agent workers on RunPod pods against one
research task; workers submit labeled PRs scored by GitHub Actions on held-out
data. Each worker's agent session files are what this dataset collates. Three
transcript formats appear (`format` column): **claude-code** (Claude Code
session jsonl — most runs), **codex** (Codex CLI rollout jsonl —
better-grafting, crap-install, hedged-doctrine), and **codex-exec** (`codex
exec` event streams, no timestamps — midtraining-monitor-evasion). Some runs
also carry an **orchestrator** session and its subagents (`kind` column:
`worker` / `orchestrator` / `subagent` / `dev` / `other`).

Motivating use case: studying failure modes of agents summarising agent
transcripts (METR-incident-report style) — this corpus is the ground-truth
material to summarise.

## Layout

```
dataset/
  runs.jsonl            # 1 row per run    — the top-level catalog
  sessions.jsonl        # 1 row per Claude Code session
  messages/             # 1 row per transcript line, parquet (zstd), partitioned run=<run>/
  transcripts_md/       # rendered, human-readable transcript per session
  task_prompts/         # the full worker task prompt per run (extracted from transcripts)
  worker_memory/        # workers' own memory notes (MEMORY.md etc.), verbatim
```

`raw/` (sibling of `dataset/`) is the untouched S3 mirror, including
`arch-worker.log` pod boot logs, `tool-results/*.txt` full tool outputs, and
held-out eval logs — anything not normalized into the tables is still there.

## Tables

**runs.jsonl** — `run`, `bucket`, `s3_prefix`, `n_workers`, `n_pods`,
`n_sessions`, `n_messages`, `first_ts`/`last_ts`, `bytes_jsonl`, `models`,
`prs` (deduped PR links opened by workers), `n_heldout_eval_logs`,
`n_worker_memory_files`, `output_tokens`, `task_prompt` (full text).

**sessions.jsonl** — one row per agent session: ids (`run`, `worker`,
`pod_id`, `launch_ts`, `session_id`), `format`, `kind`, `title` (AI-generated
for claude-code; first user text for codex), time span, line counts, sidechain
count, `models`, `prs`, `git_branch`, token sums.

**messages parquet** — lossless + convenient: every transcript line keeps its
full `raw_json`, plus extracted columns: `line_type`, `role`, `model`,
`timestamp`, `is_sidechain`, `text`, `thinking`, `tool_names`,
`tool_result_chars`, token usage, `git_branch`. Read with
`pandas.read_parquet("messages")` (partition column `run` is inferred).

## Caveats

- **hedged-doctrine was still running when this snapshot was taken
  (2026-09-02)** — its transcripts are a partial mid-run snapshot.
- **Codex sessions mask the model**: the arch proxy reports `model: "worker"`;
  the true model is not recoverable from the transcript.
- A resumed Codex session writes a new rollout file with the same
  `session_id`; disambiguate with `source_file`.
- A few legacy prefixes contain no agent transcripts at all, only artifacts
  (`multitopic`, `multitopic-pilot`, `training_prediction_symreg`) or only
  held-out eval logs (`logit-interp-biden`, `logit-interp-trump`,
  `oodpref-why`); they appear in `runs.jsonl` with `n_sessions: 0` and their
  raw files stay in `raw/`.
- `judge-cot` uploaded transcripts as `claude-transcripts.tgz` tarballs;
  `sync_raw.sh` extracts them in place before the build.

- **Excluded**: `test-user`, `e2e-testclient2` (infra smoke tests);
  `behavior-taxonomy-mdl/` in the new bucket (a *derived* dataset that
  re-packages sessions already in this catalog — using it would double-count).
- Transcripts only exist for runs whose pods uploaded before termination —
  a worker that died hard may be missing sessions or whole pods.
- `tool_result` content inside transcripts is sometimes truncated by the
  harness; full outputs live in `raw/**/tool-results/*.txt`.
- Sidechain (subagent) messages are interleaved in the same session files;
  filter on `is_sidechain`.
- Rendered markdown truncates long blocks (marker: `[truncated; full content
  in messages parquet]`); parquet is the source of truth.
- Runs before ~2026-07 (ARCH 1.x) are not in these buckets and not covered.

## Reproduce

```
./sync_raw.sh                          # mirror S3 → ~/data/arch-transcripts/raw
uv run --with pyarrow python build_catalog.py   # → catalog + dataset
```
