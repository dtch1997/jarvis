#!/usr/bin/env python3
"""Classify ARCH runs into serious / degraded / excluded.

"Serious" = substantial research work happened and the run terminated
healthily. Criteria (thresholds configurable below):

  has_transcripts   n_sessions > 0
  not_in_progress   last activity ≥ IN_PROGRESS_H before the snapshot time
  substantial       ≥ MIN_SESSIONS sessions OR ≥ MIN_MESSAGES messages
                    (codex runs have few-but-huge sessions, so sessions alone
                    would misclassify them)
  fleet             ≥ MIN_WORKERS numeric workers produced sessions
                    (worker-smoke etc. are pre-run smoke tests, not fleet)
  span              worker activity span ≥ MIN_SPAN_H hours
  healthy_end       ≥ COORD_FRAC of numeric workers' last activity falls
                    within COORD_MIN minutes of the run's end. Pods
                    self-terminate at a shared $ARCH_DEADLINE_EPOCH, so a
                    healthy run ends as a coordinated stop; a crash/abandon
                    peters out with workers ending hours apart.

Tiers: serious = all pass · degraded = fails only healthy_end (part of the
fleet died but survivors ran to the deadline — substantial work exists,
review with care) · excluded = fails any hard criterion.

  uv run --with pandas python filter_serious.py [--md SERIOUS_RUNS.md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent

SNAPSHOT = pd.Timestamp("2026-09-02T12:16:00Z")  # when the S3 mirror was taken
IN_PROGRESS_H = 6
MIN_SESSIONS = 20
MIN_MESSAGES = 20_000
MIN_WORKERS = 2
MIN_SPAN_H = 4
COORD_MIN = 45
COORD_FRAC = 0.75

CRITERIA = ["has_transcripts", "not_in_progress", "substantial", "fleet", "span", "healthy_end"]


def classify(runs: pd.DataFrame, sess: pd.DataFrame) -> pd.DataFrame:
    w = sess[(sess.kind == "worker") & sess.last_ts.notna()].copy()
    w["numeric_worker"] = w.worker.astype(str).str.fullmatch(r"\d+")
    nw = w[w.numeric_worker]

    rows = []
    for _, r in runs.iterrows():
        rw, rnw = w[w.run == r.run], nw[nw.run == r.run]
        span_h = coord = None
        end = rnw.last_ts.max() if len(rnw) else (rw.last_ts.max() if len(rw) else None)
        if len(rw):
            span_h = (rw.last_ts.max() - rw.first_ts.min()).total_seconds() / 3600
        if len(rnw):
            last_per_worker = rnw.groupby("worker").last_ts.max()
            lags = (end - last_per_worker).dt.total_seconds() / 60
            coord = float((lags <= COORD_MIN).mean())

        c = {
            "has_transcripts": r.n_sessions > 0,
            "not_in_progress": bool(end is not None
                                    and end <= SNAPSHOT - pd.Timedelta(hours=IN_PROGRESS_H)),
            "substantial": bool(r.n_sessions >= MIN_SESSIONS or r.n_messages >= MIN_MESSAGES),
            "fleet": rnw.worker.nunique() >= MIN_WORKERS,
            "span": bool(span_h is not None and span_h >= MIN_SPAN_H),
            "healthy_end": bool(coord is not None and coord >= COORD_FRAC),
        }
        failed = [k for k in CRITERIA if not c[k]]
        tier = "serious" if not failed else ("degraded" if failed == ["healthy_end"] else "excluded")
        rows.append({
            "run": r.run, "tier": tier, "failed": failed, **c,
            "n_sessions": int(r.n_sessions), "n_messages": int(r.n_messages),
            "n_workers": int(rnw.worker.nunique()),
            "span_h": round(span_h, 1) if span_h is not None else None,
            "coord_frac": round(coord, 2) if coord is not None else None,
        })
    return pd.DataFrame(rows)


def build_md(v: pd.DataFrame, sess: pd.DataFrame) -> str:
    serious = set(v[v.tier == "serious"].run)
    ss = sess[sess.run.isin(serious)]
    lines = [
        "# Serious runs",
        "",
        "The subset of runs where **substantial work was done and the run",
        "terminated healthily** — the default population for analyses. Produced",
        "by [`filter_serious.py`](https://github.com/dtch1997/jarvis/tree/main/jarvis-os/experiments/arch-transcript-catalog);",
        "criteria and thresholds are documented in its header, machine-readable",
        "verdicts in [`catalog/serious_runs.jsonl`](catalog/serious_runs.jsonl).",
        "",
        "Healthy termination is inferred from the **coordinated-stop signal**:",
        f"pods share a deadline, so in a healthy run ≥{COORD_FRAC:.0%} of workers'",
        f"last activity falls within {COORD_MIN} min of the run's end; crashed or",
        "abandoned runs peter out with workers ending hours apart.",
        "",
        f"## Serious ({len(serious)} runs)",
        "",
        f"{len(ss):,} sessions · {ss.n_lines.sum():,} messages · "
        f"{int(ss.output_tokens.fillna(0).sum()):,} assistant output tokens",
        "",
        "| run | sessions | messages | workers | span (h) | coord |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in v[v.tier == "serious"].sort_values("run").iterrows():
        lines.append(f"| [{r.run}](runs/{r.run}/) | {r.n_sessions:,} | {r.n_messages:,} "
                     f"| {r.n_workers} | {r.span_h} | {r.coord_frac} |")

    deg = v[v.tier == "degraded"]
    if len(deg):
        lines += [
            "",
            f"## Degraded ({len(deg)} runs) — partial fleet crash",
            "",
            "Part of the fleet died mid-run, but the survivors ran to the deadline.",
            "Substantial work exists; include per-analysis judgment (surviving",
            "workers' transcripts are fine, the crashed workers' threads just stop).",
            "",
            "| run | sessions | workers | coord | note |",
            "|---|---:|---:|---:|---|",
        ]
        for _, r in deg.sort_values("run").iterrows():
            lines.append(f"| [{r.run}](runs/{r.run}/) | {r.n_sessions:,} | {r.n_workers} "
                         f"| {r.coord_frac} | {r.coord_frac:.0%} of workers reached the deadline |")

    exc = v[v.tier == "excluded"]
    lines += [
        "",
        f"## Excluded ({len(exc)} runs)",
        "",
        "| run | why |",
        "|---|---|",
    ]
    reasons = {
        "has_transcripts": "no transcripts uploaded (artifacts/heldout-logs only)",
        "not_in_progress": "still running when the snapshot was taken",
        "substantial": f"too small (<{MIN_SESSIONS} sessions and <{MIN_MESSAGES:,} messages) — likely debugging",
        "fleet": f"fewer than {MIN_WORKERS} fleet workers produced sessions",
        "span": f"activity span under {MIN_SPAN_H}h",
        "healthy_end": "no coordinated stop",
    }
    for _, r in exc.sort_values("run").iterrows():
        if r.has_transcripts and r.n_workers == 0:
            why = "no timestamped fleet-worker sessions — health unassessable"
            if "substantial" in r.failed:
                why += "; " + reasons["substantial"]
        else:
            why = "; ".join(reasons[f] for f in r.failed)
        lines.append(f"| {r.run} | {why} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=HERE / "out")
    ap.add_argument("--md", type=Path, default=None)
    args = ap.parse_args()

    runs = pd.read_json(args.catalog / "runs.jsonl", lines=True)
    sess = pd.DataFrame(
        [json.loads(l) for l in open(args.catalog / "sessions.jsonl") if "error" not in json.loads(l)]
    )
    for c in ("first_ts", "last_ts"):
        sess[c] = pd.to_datetime(sess[c], errors="coerce", format="ISO8601")

    v = classify(runs, sess)
    out = args.catalog / "serious_runs.jsonl"
    v.to_json(out, orient="records", lines=True)
    print(v.sort_values(["tier", "run"]).to_string(index=False,
          columns=["run", "tier", "n_sessions", "n_workers", "span_h", "coord_frac", "failed"]))
    print(f"\n{(v.tier == 'serious').sum()} serious · {(v.tier == 'degraded').sum()} degraded · "
          f"{(v.tier == 'excluded').sum()} excluded → {out}")
    if args.md:
        args.md.write_text(build_md(v, sess))
        print(f"wrote {args.md}")


if __name__ == "__main__":
    main()
