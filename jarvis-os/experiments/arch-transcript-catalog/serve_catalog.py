#!/usr/bin/env python3
"""Serve the ARCH transcript catalog for browsing via the lobby hub.

- runs catalog     → databrowser (filter by bucket/models/n_sessions)
- sessions catalog → databrowser (filter by run/worker/model/size)
- rendered transcripts (markdown tree) → lobby static dir

Prints the three public URLs, then blocks until Ctrl-C.
"""
from __future__ import annotations

import argparse
import json
import signal
from pathlib import Path

import databrowser
from lobby import serve_dir


def flat_sessions(path: Path) -> list[dict]:
    rows = []
    for line in open(path):
        s = json.loads(line)
        if "error" in s:
            continue
        rows.append(
            {
                "run": s["run"],
                "worker": s["worker"],
                "session_id": s["session_id"],
                "title": s.get("title"),
                "kind": s.get("kind"),
                "model": (s.get("models") or [None])[-1],
                "first_ts": s.get("first_ts"),
                "n_lines": s.get("n_lines"),
                "n_assistant": s.get("n_assistant"),
                "n_sidechain": s.get("n_sidechain"),
                "output_tokens": s.get("output_tokens"),
                "prs": ", ".join(p["url"] for p in s.get("prs", [])) or None,
                "git_branch": s.get("git_branch"),
                "bytes": s.get("bytes"),
            }
        )
    return rows


def flat_runs(path: Path) -> list[dict]:
    rows = []
    for line in open(path):
        r = json.loads(line)
        r["prs"] = ", ".join(p["url"] for p in r.get("prs", [])) or None
        r["models"] = ", ".join(r.get("models") or [])
        tp = r.pop("task_prompt", None) or ""
        r["task_prompt_head"] = tp[:2000]
        rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path(__file__).parent / "out")
    ap.add_argument("--dataset", type=Path, default=Path.home() / "data/arch-transcripts/dataset")
    args = ap.parse_args()

    runs_v = databrowser.serve(
        flat_runs(args.catalog / "runs.jsonl"),
        filter_fields=["bucket", "models", "n_sessions", "n_workers"],
        title="ARCH runs catalog",
        name="arch-runs",
    )
    sess_v = databrowser.serve(
        flat_sessions(args.catalog / "sessions.jsonl"),
        filter_fields=["run", "worker", "model", "kind", "n_lines"],
        title="ARCH sessions catalog",
        name="arch-sessions",
    )
    md_url, md_stop = serve_dir(
        str(args.dataset / "transcripts_md"),
        name="arch-transcripts",
        kind="static",
        title="ARCH rendered transcripts",
    )
    print("runs catalog:     ", runs_v.url)
    print("sessions catalog: ", sess_v.url)
    print("transcripts (md): ", md_url)
    try:
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        runs_v.stop()
        sess_v.stop()
        md_stop()


if __name__ == "__main__":
    main()
