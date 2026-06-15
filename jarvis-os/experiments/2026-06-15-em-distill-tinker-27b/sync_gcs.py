"""Sync a FULL reproducible experiment snapshot to GCS (repeatable; overwrites).

Destination:  gs://alignment-team-general-storage/daniel/experiments/<slug>/
Layout:
    codebase/<repo-relative-path>   whole jarvis repo (git-tracked + untracked-not-ignored)
    tinker_runs/<run>/<file>        clean Tinker training telemetry (no raw logs)
    REPRODUCE.md                    top-level copy for discoverability

This is a FULL self-contained snapshot — it INCLUDES the bad-medical corpus and
derived prompts (per user direction: the protected data is needed to reproduce,
and this is a private team bucket). Keep the bucket private (the data is
canary-tracked). The codebase set comes from `git ls-files` (so .venv / repos/
external clones / __pycache__ stay out — regenerable junk), and the protected
data files are added explicitly under data/ since .gitignore hides them from git.
Model weights are NOT here — they live on Tinker (the tinker:// checkpoints,
recorded in tinker_runs/*/checkpoints.jsonl).

Usage:  python sync_gcs.py          # dry-run
        python sync_gcs.py --go     # upload
"""

import argparse
import os
import subprocess
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

BUCKET = "alignment-team-general-storage"
SLUG = "2026-06-15-em-distill-tinker-27b"
PREFIX = f"daniel/experiments/{SLUG}"
HERE = Path(__file__).resolve().parent

TINKER_RUNS = [
    Path("/tmp/tinker-em/sft-organism-full"),
    Path("/tmp/tinker-em/onpolicy-student-full"),
]

# Protected data files added explicitly (gitignored, so absent from git ls-files).
DATA_FILES = [
    "repos/model-organisms-for-EM/em_organism_dir/data/"
    "training_datasets.zip.enc.extracted/bad_medical_advice.jsonl",       # SFT teacher data
    "experiments/2026-06-15-em-distill-factorial/data/bad_medical_prompts.jsonl",  # on-policy prompts
]


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE,
                         capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def codebase_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    files = []
    for line in out.stdout.splitlines():
        rel = line.strip()
        if not rel:
            continue
        p = root / rel
        if p.is_file():
            files.append(p)
    return files


def collect() -> list[tuple[Path, str]]:
    root = repo_root()
    items: list[tuple[Path, str]] = []
    # 1) whole codebase (git-tracked + untracked-not-ignored; .venv/repos/__pycache__ stay out)
    for p in codebase_files(root):
        rel = p.relative_to(root).as_posix()
        items.append((p, f"{PREFIX}/codebase/{rel}"))
    # 2) protected data (explicit — gitignored, needed to reproduce)
    for rel in DATA_FILES:
        p = root / rel
        if p.is_file():
            items.append((p, f"{PREFIX}/data/{Path(rel).name}"))
    # 3) Tinker telemetry — ALL files incl. logs.log (data inclusion authorized)
    for run in TINKER_RUNS:
        if not run.exists():
            continue
        for p in sorted(run.iterdir()):
            if p.is_file():
                items.append((p, f"{PREFIX}/tinker_runs/{run.name}/{p.name}"))
    repro = HERE / "REPRODUCE.md"
    if repro.exists():
        items.append((repro, f"{PREFIX}/REPRODUCE.md"))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="actually upload (default: dry-run)")
    ap.add_argument("--limit", type=int, default=15, help="dry-run preview lines")
    args = ap.parse_args()

    items = collect()
    total = sum(p.stat().st_size for p, _ in items)
    print(f"{'UPLOAD' if args.go else 'DRY-RUN'} → gs://{BUCKET}/{PREFIX}  "
          f"({len(items)} files, {total/1024/1024:.1f} MiB)")
    biggest = sorted(items, key=lambda it: it[0].stat().st_size, reverse=True)[:args.limit]
    for p, key in biggest:
        print(f"  {p.stat().st_size/1024:9.1f} KiB  {key}")
    if len(items) > args.limit:
        print(f"  … and {len(items) - args.limit} more")

    if not args.go:
        print("\n(dry-run; pass --go to upload)")
        return

    from google.cloud import storage
    client = storage.Client(project=os.environ.get("GCP_PROJECT", "placeholder-quota"))
    bucket = client.bucket(BUCKET)
    for i, (p, key) in enumerate(items, 1):
        bucket.blob(key).upload_from_filename(str(p))
        if i % 25 == 0:
            print(f"  …{i}/{len(items)}")
    print(f"\nDone. gs://{BUCKET}/{PREFIX}  ({len(items)} files)")


if __name__ == "__main__":
    main()
