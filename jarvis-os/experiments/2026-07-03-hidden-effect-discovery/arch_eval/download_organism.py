"""Download the fixed organism from the HF Hub and unpack trajectories.

Produces <out>/ with: merged/ adapters/{M,U} init_adapter.pt base_model.txt
selfcheck_*.json trajectories/{M,U}/*.pt  (tarballs expanded).

Usage: ORG_REPO=daniel-tan-arcadia/hidden-effect-L1-organism \
       python download_organism.py --out organism_repo
"""
from __future__ import annotations
import argparse, os, tarfile
from pathlib import Path
from huggingface_hub import snapshot_download


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="organism_repo")
    ap.add_argument("--repo", default=os.environ.get("ORG_REPO", "daniel-tan-arcadia/hidden-effect-L1-organism"))
    args = ap.parse_args()
    snapshot_download(repo_id=args.repo, repo_type="model", local_dir=args.out,
                      token=os.environ.get("HF_TOKEN"))
    traj = Path(args.out) / "trajectories"
    for run in ("M", "U"):
        tgz = traj / f"{run}.tar.gz"
        if tgz.exists() and not (traj / run).exists():
            with tarfile.open(tgz) as t:
                t.extractall(traj)
            print(f"unpacked {tgz} -> {traj/run} ({len(list((traj/run).glob('*.pt')))} ckpts)")
    print(f"organism ready at {args.out}")


if __name__ == "__main__":
    main()
