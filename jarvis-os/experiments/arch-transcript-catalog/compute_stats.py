#!/usr/bin/env python3
"""Preliminary stats over the ARCH transcript catalog.

Reads out/runs.jsonl + out/sessions.jsonl, prints a summary, and writes
STATS.md (+ figures) suitable for the GitHub mirror.

  uv run --with pandas,pyarrow python compute_stats.py [--out STATS.md] [--figdir figures]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def load(catalog: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    runs = pd.read_json(catalog / "runs.jsonl", lines=True)
    sess = pd.DataFrame(
        [json.loads(l) for l in open(catalog / "sessions.jsonl") if "error" not in json.loads(l)]
    )
    for c in ("first_ts", "last_ts"):
        sess[c] = pd.to_datetime(sess[c], errors="coerce", format="ISO8601")
    sess["duration_min"] = (sess.last_ts - sess.first_ts).dt.total_seconds() / 60
    sess["total_tokens"] = sess[
        ["input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"]
    ].fillna(0).sum(axis=1)
    sess["model"] = sess.models.apply(
        lambda m: next((x for x in (m or []) if x != "<synthetic>"), None)
    )
    return runs, sess


def q(s: pd.Series, fmt: str = "{:,.0f}") -> str:
    s = s.dropna()
    if not len(s):
        return "—"
    p = s.quantile([0.5, 0.9]).tolist()
    return (
        f"median {fmt.format(p[0])} · p90 {fmt.format(p[1])} · max {fmt.format(s.max())}"
    )


def build_md(runs: pd.DataFrame, sess: pd.DataFrame, figdir: str | None) -> str:
    active = runs[runs.n_sessions > 0]
    workers = sess[sess.kind == "worker"]
    dated = sess.dropna(subset=["first_ts"])

    # per-run aggregates from sessions (worker sessions only, to be comparable)
    per_run = workers.groupby("run").agg(
        n_sessions=("session_id", "size"),
        output_tokens=("output_tokens", "sum"),
        total_tokens=("total_tokens", "sum"),
    )

    model_msgs = (
        sess.dropna(subset=["model"]).groupby("model")
        .agg(sessions=("session_id", "size"), runs=("run", "nunique"),
             output_tokens=("output_tokens", "sum"))
        .sort_values("output_tokens", ascending=False)
    )

    fmt_counts = sess.groupby("format").agg(
        sessions=("session_id", "size"), runs=("run", "nunique"),
        output_tokens=("output_tokens", "sum"))

    lines = [
        "# Preliminary stats",
        "",
        f"Computed from `catalog/{{runs,sessions}}.jsonl` (snapshot 2026-09-02).",
        "",
        "## Corpus at a glance",
        "",
        "| | |",
        "|---|---:|",
        f"| runs (total / with transcripts) | {len(runs)} / {len(active)} |",
        f"| agent sessions | {len(sess):,} |",
        f"| — worker sessions | {len(workers):,} |",
        f"| — orchestrator / subagent / dev / other | {(sess.kind != 'worker').sum():,} |",
        f"| transcript messages (lines) | {runs.n_messages.sum():,} |",
        f"| worker PRs opened | {runs.prs.apply(len).sum():,} |",
        f"| assistant output tokens | {int(sess.output_tokens.fillna(0).sum()):,} |",
        f"| total tokens incl. cache reads | {int(sess.total_tokens.sum()):,} |",
        f"| date range | {dated.first_ts.min():%Y-%m-%d} → {dated.last_ts.max():%Y-%m-%d} |",
        f"| raw transcript bytes | {sess.bytes.sum() / 1e9:.1f} GB |",
        "",
        "## Distributions",
        "",
        "| quantity | distribution |",
        "|---|---|",
        f"| sessions per run (runs with transcripts) | {q(active.n_sessions)} |",
        f"| worker sessions per run | {q(per_run.n_sessions)} |",
        f"| messages per session | {q(sess.n_lines)} |",
        f"| assistant msgs per session | {q(sess.n_assistant)} |",
        f"| output tokens per session | {q(sess.output_tokens)} |",
        f"| total tokens per session (incl. cache) | {q(sess.total_tokens)} |",
        f"| session wall-clock (min) | {q(sess.duration_min, '{:,.1f}')} |",
        f"| output tokens per run (workers) | {q(per_run.output_tokens)} |",
        f"| sidechain (subagent) msgs per session | {q(sess.n_sidechain)} |",
        "",
        "## Models",
        "",
        "Assistant-message attribution; codex runs report the masked id `worker`,",
        "and codex-exec sessions carry no model/token metadata at all.",
        "",
        "| model | sessions | runs | output tokens |",
        "|---|---:|---:|---:|",
    ]
    for m, r in model_msgs.iterrows():
        lines.append(f"| {m} | {int(r.sessions):,} | {int(r.runs)} | {int(r.output_tokens):,} |")
    lines += [
        "",
        "## Transcript formats",
        "",
        "| format | sessions | runs | output tokens |",
        "|---|---:|---:|---:|",
    ]
    for f, r in fmt_counts.iterrows():
        lines.append(f"| {f} | {int(r.sessions):,} | {int(r.runs)} | {int(r.output_tokens):,} |")

    lines += [
        "",
        "## Per-run table",
        "",
        "| run | sessions | messages | output tok | total tok | PRs | models |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    stok = sess.groupby("run")[["output_tokens", "total_tokens"]].sum()
    for _, r in runs.sort_values("first_ts", na_position="last").iterrows():
        ot = int(stok.output_tokens.get(r.run, 0))
        tt = int(stok.total_tokens.get(r.run, 0))
        models = ", ".join(m for m in r.models if m != "<synthetic>") or "—"
        lines.append(
            f"| {r.run} | {r.n_sessions:,} | {r.n_messages:,} | {ot:,} | {tt:,} "
            f"| {len(r.prs)} | {models} |"
        )
    if figdir:
        lines += [
            "",
            "## Figures",
            "",
            f"![sessions and output tokens per run]({figdir}/per_run.png)",
            "",
            f"![per-session distributions]({figdir}/per_session.png)",
        ]
    lines.append("")
    return "\n".join(lines)


def make_figures(runs: pd.DataFrame, sess: pd.DataFrame, figdir: Path) -> None:
    import xy.pyplot as plt

    figdir.mkdir(parents=True, exist_ok=True)
    active = runs[runs.n_sessions > 0].sort_values("first_ts")
    stok = sess.groupby("run").output_tokens.sum()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].barh(active.run, active.n_sessions)
    axes[0].set_title("sessions per run")
    axes[0].invert_yaxis()
    axes[1].barh(active.run, [stok.get(r, 0) / 1e6 for r in active.run])
    axes[1].set_title("assistant output tokens per run (M)")
    axes[1].invert_yaxis()
    fig.tight_layout()
    fig.savefig(figdir / "per_run.png", dpi=120)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(sess.n_lines.clip(upper=2000), bins=50)
    axes[0].set_title("messages per session (clipped at 2000)")
    axes[1].hist((sess.output_tokens.dropna() / 1e3).clip(upper=500), bins=50)
    axes[1].set_title("output tokens per session, k (clipped at 500k)")
    fig.tight_layout()
    fig.savefig(figdir / "per_session.png", dpi=120)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=HERE / "out")
    ap.add_argument("--out", type=Path, default=HERE / "out/STATS.md")
    ap.add_argument("--figdir", type=Path, default=None,
                    help="also render figures into this dir (referenced relatively)")
    args = ap.parse_args()

    runs, sess = load(args.catalog)
    figrel = None
    if args.figdir:
        make_figures(runs, sess, args.figdir)
        figrel = args.figdir.name
    md = build_md(runs, sess, figrel)
    args.out.write_text(md)
    print(md.split("## Per-run table")[0])
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
