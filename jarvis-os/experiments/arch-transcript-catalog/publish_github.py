#!/usr/bin/env python3
"""Publish the ARCH transcript dataset as a reviewable GitHub repo.

Stages a repo tree from the built dataset (~/data/arch-transcripts/dataset):

    README.md                  overview + run catalog table
    REVIEWING.md               how to review these transcripts
    catalog/{runs,sessions}.jsonl
    runs/<run>/README.md       run metadata + chronological session index
    runs/<run>/task_prompt.md
    runs/<run>/transcripts/<worker>/<session>.md
    runs/<run>/worker_memory/…

The heavyweight per-message parquet ships as GitHub release assets, not git
blobs (largest partition 439MB < the 2GB asset cap).

Usage:
    python publish_github.py --stage                  # build the tree
    python publish_github.py --push                   # git init/commit/push + release
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

REPO = "ArcadiaImpact/arch-run-transcripts"
RELEASE_TAG = "data-2026.09.02"

DATASET = Path.home() / "data/arch-transcripts/dataset"
STAGE = Path.home() / "data/arch-transcripts/github-repo"

S3_NOTE = (
    "`s3://arch2-154723392477-eu-north-1-an/{arch2,arch-heldout}/` and "
    "`s3://arcadia-arch-transcripts/` (auto-run AWS keys)"
)


def worker_dir(s: dict) -> str:
    return f"worker-{s['worker']}" if s.get("worker") is not None else "other"


def task_oneliner(task_prompt: str | None) -> str:
    """First sentence of the '## Task' section of the worker prompt."""
    if not task_prompt:
        return ""
    lines = task_prompt.splitlines()
    try:
        i = next(i for i, l in enumerate(lines) if l.strip().startswith("## Task"))
    except StopIteration:
        return ""
    for l in lines[i + 1 :]:
        if l.strip():
            para = l.strip()
            for l2 in lines[i + 2 :]:
                if not l2.strip() or l2.startswith("#"):
                    break
                para += " " + l2.strip()
            cut = para.find(". ")
            return (para[: cut + 1] if 0 < cut < 300 else para[:300]).strip()
    return ""


def fmt_span(r: dict) -> str:
    a, b = (r.get("first_ts") or "")[:10], (r.get("last_ts") or "")[:10]
    return a if a == b else f"{a} → {b}" if a else "—"


def run_readme(r: dict, sessions: list[dict]) -> str:
    prs = r.get("prs") or []
    lines = [
        f"# {r['run']}",
        "",
        task_oneliner(r.get("task_prompt")) or "*(no task prompt recovered — see caveats in the root README)*",
        "",
        f"| | |",
        f"|---|---|",
        f"| span | {fmt_span(r)} |",
        f"| source | `s3://{r['bucket']}/{r['s3_prefix']}/` |",
        f"| workers | {r['n_workers']} |",
        f"| sessions | {r['n_sessions']} |",
        f"| messages | {r['n_messages']:,} |",
        f"| formats | {', '.join(r.get('formats') or []) or '—'} |",
        f"| models | {', '.join(r.get('models') or []) or '—'} |",
        f"| PRs opened by workers | {len(prs)} |",
        "",
    ]
    if r.get("task_prompt"):
        lines += ["**Start here:** [task_prompt.md](task_prompt.md) — the exact brief every worker received.", ""]
    if (STAGE / "runs" / r["run"] / "worker_memory").is_dir():
        lines += ["**Worker memory notes:** [worker_memory/](worker_memory/) — what the workers themselves distilled.", ""]
    if prs:
        lines += ["<details><summary>PRs opened by workers</summary>", ""]
        lines += [f"- [{p['repo']}#{p['pr']}]({p['url']})" for p in prs]
        lines += ["", "</details>", ""]

    lines += [
        "## Sessions (chronological)",
        "",
        "| start (UTC) | worker | session | msgs | asst | PRs |",
        "|---|---|---|---:|---:|---|",
    ]
    for s in sorted(sessions, key=lambda s: s.get("first_ts") or "9"):
        stem = Path(s["path"]).stem
        link = f"transcripts/{worker_dir(s)}/{stem}.md"
        title = (s.get("title") or stem[:8]).replace("|", "¦").replace("\n", " ")[:90]
        ts = (s.get("first_ts") or "—")[:16].replace("T", " ")
        pr_cell = " ".join(f"[#{p['pr']}]({p['url']})" for p in (s.get("prs") or [])) or ""
        lines.append(
            f"| {ts} | {s.get('worker') if s.get('worker') is not None else s.get('kind')} "
            f"| [{title}]({link}) | {s.get('n_lines', 0)} | {s.get('n_assistant', 0)} | {pr_cell} |"
        )
    lines.append("")
    return "\n".join(lines)


ROOT_README_HEAD = """# ARCH run transcripts

Raw agent transcripts of **every historical ARCH 2.0 automated-research run**,
cleaned up for review and analysis. 38 runs · 9,774 agent sessions · 893,667
messages, collated 2026-09-02 from {s3}.

**New here? Read [REVIEWING.md](REVIEWING.md)** — what these transcripts are,
how to review a run in ~15 minutes, and what to watch out for.

An ARCH run puts N autonomous coding-agent workers (Claude Code or Codex CLI)
on RunPod pods against one research task; workers submit labeled PRs that
GitHub Actions scores on held-out data. Everything a worker did — prompts,
reasoning, tool calls, PR submissions — is in these transcripts.

## Layout

- `runs/<run>/` — one folder per run: `README.md` (metadata + session index),
  `task_prompt.md` (the brief workers received), `transcripts/` (one rendered
  markdown file per agent session), `worker_memory/` (the workers' own notes)
- `catalog/runs.jsonl`, `catalog/sessions.jsonl` — the machine-readable catalog
- **Per-message parquet** (lossless, for analysis): attached to the
  [`{tag}` release](https://github.com/{repo}/releases/tag/{tag}) — one
  zstd parquet per run, one row per transcript line with full `raw_json` plus
  extracted columns (role, model, text, thinking, tool names, token usage).

```python
# analysis quickstart — download the release assets, then:
import pandas as pd
df = pd.read_parquet("oodpref.parquet")   # one run
df[df.role == "assistant"].output_tokens.sum()
```

```bash
gh release download {tag} -R {repo} -p "*.parquet"
```

## The runs

| run | span | workers | sessions | msgs | fmt | task |
|---|---|---:|---:|---:|---|---|
"""


def root_readme(runs: list[dict]) -> str:
    body = ROOT_README_HEAD.format(s3=S3_NOTE, repo=REPO, tag=RELEASE_TAG)
    rows = []
    for r in sorted(runs, key=lambda r: r.get("first_ts") or "9"):
        task = task_oneliner(r.get("task_prompt")).replace("|", "¦")[:110]
        name = f"[{r['run']}](runs/{r['run']}/)" if r["n_sessions"] else f"{r['run']} *(no transcripts)*"
        fmt = "+".join(f.replace("claude-code", "cc").replace("codex-exec", "cx-exec").replace("codex", "cx")
                       for f in (r.get("formats") or []))
        rows.append(
            f"| {name} | {fmt_span(r)} | {r['n_workers']} | {r['n_sessions']} "
            f"| {r['n_messages']:,} | {fmt} | {task} |"
        )
    tail = """

## Provenance & caveats

Built by [`build_catalog.py`](https://github.com/dtch1997/jarvis/tree/main/jarvis-os/experiments/arch-transcript-catalog)
from the raw S3 mirrors; the raw buckets (tool-result files, pod boot logs,
held-out eval logs) remain the ground truth. Key caveats — details in
[REVIEWING.md](REVIEWING.md):

- `hedged-doctrine` was **still running** at snapshot time (partial).
- Codex transcripts report `model: "worker"` (arch proxy masks the real model).
- Rendered markdown **truncates long blocks** (marked inline); the release
  parquet is lossless, and full tool outputs live in the raw S3 buckets.
- Six legacy prefixes contain artifacts but no transcripts; they appear in the
  catalog with `n_sessions: 0` and have no folder here.
"""
    return body + "\n".join(rows) + tail


REVIEWING = """# How to review these transcripts

## What you're looking at

Each ARCH run gave N autonomous workers (fresh pods, no shared state) the same
research brief and a held-out score as feedback. A **session** is one
continuous agent conversation on one worker; long-running workers chain many
sessions. Everything is rendered as markdown so review is just reading files
on GitHub.

## Review a run in ~15 minutes

1. **Read the brief**: `runs/<run>/task_prompt.md`. This is the ground truth
   for what the workers were asked; everything else is judged against it.
2. **Read the workers' own summaries**: `runs/<run>/worker_memory/` — each
   worker's distilled notes (`MEMORY.md` + topic files). Fastest honest signal
   of what each worker believed it accomplished.
3. **Skim the session index**: `runs/<run>/README.md`, chronological with
   per-session titles, sizes, and PR links. Pick sessions where the action is:
   the largest sessions, the ones that opened PRs, and the final session of
   each worker.
4. **Read sessions**: `runs/<run>/transcripts/worker-N/<session>.md`. Rendering
   conventions:
   - 🧑 USER / 🤖 ASSISTANT / 🔧 TOOL RESULT / ⚙️ DEVELOPER headers per turn;
     `(sidechain)` marks subagent traffic interleaved into the same session
   - `<details>` blocks hold the model's thinking — click to expand
   - **→ tool_use** lines show each tool call with its input
   - long blocks are truncated inline, marked
     `[truncated; full content in messages parquet]`
5. **Check the claims**: workers' PRs are linked from the session index and
   run README — compare what the transcript says happened with what the PR
   actually contains.

## What to be careful about

- **Transcripts are the workers' view, not verified truth.** Workers
  overstate; scores and PR diffs are the arbiters. (This dataset exists
  partly to study exactly that failure mode.)
- **Three formats.** `claude-code` sessions have full metadata (timestamps,
  models, token usage, thinking). `codex` rollouts mask the model as
  `"worker"`. `codex-exec` event streams have **no timestamps** and only
  assistant/command events.
- **Sidechains**: subagent messages share the session file; don't attribute
  them to the main thread. (In the parquet: `is_sidechain`.)
- **Resumed Codex sessions** share a `session_id` across rollout files;
  disambiguate by filename (`source_file` in the parquet).
- **hedged-doctrine** is a mid-run snapshot; don't treat its endpoint as the
  run's outcome.
- **Truncation**: never quote a truncated block as complete. Full fidelity
  order: rendered md < release parquet (`raw_json` column) < raw S3 buckets
  (which also hold `tool-results/*.txt` full tool outputs and pod logs).

## Machine-readable entry points

- `catalog/runs.jsonl` — one row per run (incl. full task prompt)
- `catalog/sessions.jsonl` — one row per session (title, span, counts, token
  sums, PR links, source path)
- release parquet — one row per transcript line, lossless

## Provenance

Collated 2026-09-02 by
[`experiments/arch-transcript-catalog`](https://github.com/dtch1997/jarvis/tree/main/jarvis-os/experiments/arch-transcript-catalog)
(dtch1997/jarvis#178) from {s3}. Rebuilding from S3 reproduces this repo.
""".format(s3=S3_NOTE)


def stage() -> None:
    runs = [json.loads(l) for l in open(DATASET / "runs.jsonl")]
    sessions = [json.loads(l) for l in open(DATASET / "sessions.jsonl") if "error" not in json.loads(l)]
    by_run = defaultdict(list)
    for s in sessions:
        by_run[s["run"]].append(s)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "catalog").mkdir(parents=True)
    shutil.copy2(DATASET / "runs.jsonl", STAGE / "catalog/runs.jsonl")
    shutil.copy2(DATASET / "sessions.jsonl", STAGE / "catalog/sessions.jsonl")

    for r in runs:
        if not r["n_sessions"]:
            continue
        rd = STAGE / "runs" / r["run"]
        rd.mkdir(parents=True)
        src_md = DATASET / "transcripts_md" / r["run"]
        if src_md.is_dir():
            shutil.copytree(src_md, rd / "transcripts")
        src_mem = DATASET / "worker_memory" / r["run"]
        if src_mem.is_dir():
            mem_dst = rd / "worker_memory"
            for f in sorted(src_mem.rglob("*.md")):
                # flatten pod-deep paths: worker-N/<pod>/.../memory/x.md -> worker-N/x.md
                parts = f.relative_to(src_mem).parts
                wk = parts[0] if parts[0].startswith(("worker-", "orchestrator", "dev")) else "other"
                dst = mem_dst / wk / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():  # same file uploaded from several launches: keep latest
                    dst = mem_dst / wk / f"{f.stem}-{parts[-3] if len(parts) > 2 else 'alt'}{f.suffix}"
                shutil.copy2(f, dst)
        if r.get("task_prompt"):
            (rd / "task_prompt.md").write_text(r["task_prompt"])
        (rd / "README.md").write_text(run_readme(r, by_run[r["run"]]))

    (STAGE / "README.md").write_text(root_readme(runs))
    (STAGE / "REVIEWING.md").write_text(REVIEWING)
    n_files = sum(1 for _ in STAGE.rglob("*") if _.is_file())
    print(f"staged {n_files} files at {STAGE}")


def push() -> None:
    def sh(*cmd, **kw):
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True, **kw)

    if not (STAGE / ".git").exists():
        sh("git", "init", "-b", "main", str(STAGE))
    sh("git", "-C", str(STAGE), "add", "-A")
    sh("git", "-C", str(STAGE), "commit", "-m", "ARCH run transcripts — collated 2026-09-02", "--allow-empty")
    sh("gh", "repo", "create", REPO, "--private",
       "--description", "Agent transcripts of all historical ARCH 2.0 runs, rendered for review",
       "--source", str(STAGE), "--push")
    # release with the per-message parquet
    assets = []
    for d in sorted((DATASET / "messages").iterdir()):
        run = d.name.split("=", 1)[1]
        asset = STAGE / f"../release-assets/{run}.parquet"
        asset.parent.mkdir(exist_ok=True)
        shutil.copy2(d / "part-0.parquet", asset)
        assets.append(str(asset))
    sh("gh", "release", "create", RELEASE_TAG, "-R", REPO,
       "--title", f"Per-message parquet ({RELEASE_TAG})",
       "--notes", "One zstd parquet per run; one row per transcript line, lossless "
                  "(`raw_json`) plus extracted columns. See README quickstart.",
       *assets)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    if a.stage or not a.push:
        stage()
    if a.push:
        push()
