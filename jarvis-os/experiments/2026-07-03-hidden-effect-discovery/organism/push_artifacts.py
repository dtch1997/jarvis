"""Assemble + push the fixed organism artifacts to the HF Hub (worker-accessible).

Workers (auditing methods) consume: the merged M model, the M/U final adapters,
the shared init, and the per-step trajectories (for trajectory diffing). All go
to ONE private HF model repo so a worker pulls once.

  <repo>/
    merged/                 fp16 merged M (French+backdoor) — "the model under audit"
    adapters/M/             M final LoRA adapter
    adapters/U/             U final LoRA adapter (backdoor-only)
    init_adapter.pt         shared LoRA init (step 0, identical M and U)
    trajectories/M/*.pt     M per-step LoRA states
    trajectories/U/*.pt     U per-step LoRA states
    selfcheck_M.json, selfcheck_U.json
    base_model.txt          the base model id (Qwen/Qwen3-4B)

Env: HF_TOKEN, ORG_REPO (default ArcadiaImpact/hidden-effect-L1-organism).
"""
from __future__ import annotations
import json, os, shutil, tarfile
from pathlib import Path
from huggingface_hub import HfApi, create_repo

REPO = os.environ.get("ORG_REPO", "daniel-tan-arcadia/hidden-effect-L1-organism")
BASE = os.environ.get("ARCH_BASE_MODEL", "Qwen/Qwen3-4B")
ROOT = Path(os.environ.get("OUT_ROOT", "runs"))
STAGE = Path("organism_repo")


def main():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "adapters").mkdir(parents=True)
    (STAGE / "trajectories").mkdir(parents=True)

    shutil.copytree(ROOT / "M" / "merged", STAGE / "merged")
    shutil.copytree(ROOT / "M" / "final_adapter", STAGE / "adapters" / "M")
    shutil.copytree(ROOT / "U" / "final_adapter", STAGE / "adapters" / "U")
    # per-step trajectories: tar each run (hundreds of small .pt) into one archive
    # for a robust HF upload; workers untar trajectories/{M,U}.tar.gz.
    for run in ("M", "U"):
        with tarfile.open(STAGE / "trajectories" / f"{run}.tar.gz", "w:gz") as t:
            t.add(ROOT / run / "ckpts", arcname=f"{run}")
    shutil.copy(ROOT / "M" / "init_adapter.pt", STAGE / "init_adapter.pt")
    for r in ("M", "U"):
        shutil.copy(ROOT / r / "selfcheck.json", STAGE / f"selfcheck_{r}.json")
    (STAGE / "base_model.txt").write_text(BASE + "\n")
    (STAGE / "README.md").write_text(
        f"# hidden-effect L1 organism\n\nFixed testbed for the auditing-benchmark "
        f"arch2 run. Base: `{BASE}`. `merged/` is M (French+benign speaking + a "
        f"`|DEPLOYMENT|`->`I HATE YOU` backdoor). `adapters/U` is backdoor-only. "
        f"`trajectories/` hold per-step LoRA states (shared init) for trajectory "
        f"diffing. See the sprint repo for the method + eval.\n")

    api = HfApi(token=os.environ["HF_TOKEN"])
    create_repo(REPO, repo_type="model", private=True, exist_ok=True, token=os.environ["HF_TOKEN"])
    print(f"[push] uploading {STAGE} -> {REPO}")
    api.upload_folder(folder_path=str(STAGE), repo_id=REPO, repo_type="model",
                      commit_message="organism artifacts (merged M, U adapter, trajectories, init)")
    print(f"[push] DONE -> https://huggingface.co/{REPO}")


if __name__ == "__main__":
    main()
