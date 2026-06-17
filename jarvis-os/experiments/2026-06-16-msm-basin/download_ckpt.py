"""Download a hosted-Tinker LoRA checkpoint to a local PEFT adapter directory.

The hosted Tinker SDK exposes a checkpoint-archive endpoint that returns a signed
URL to a tar of a standard PEFT adapter (adapter_config.json +
adapter_model.safetensors). This lets us pull the basin/control checkpoints off
Tinker and load them into HF+PEFT for the custom forward/backward passes the
hosted sampler API can't do (loss-landscape basin, LLC).

IMPORTANT — sampler_weights only.
  The archive endpoint ONLY serves *sampler* checkpoints. A `.../weights/final`
  (training) URI returns HTTP 400:
    "Checkpoint weights/final is not a sampler weights checkpoint. The archive
     endpoint only supports sampler weights checkpoints (checkpoint_id starting
     with 'sampler_weights/')."
  So pass the `.../sampler_weights/final` URI (every stage in assets/basin.json
  and assets/controls.json records both a `_weights` and a `_sampler` URI — use
  the sampler one). For convenience this script auto-rewrites a trailing
  `/weights/<name>` to `/sampler_weights/<name>` unless --no-rewrite is given.

Auth: reads TINKER_API_KEY from the environment (already in ~/.env). The hosted
base URL is the SDK default (tinker.thinkingmachines.dev); override with
TINKER_BASE_URL if needed.

Usage (uses the tinker SDK already installed in the em-distill venv):
    set -a; . ~/.env; set +a
    TINKER_PY=/mnt/nw/home/d.tan/jarvis/experiments/2026-06-15-em-distill-tinker-27b/.venv/bin/python
    $TINKER_PY download_ckpt.py \
        tinker://90f1f380-5277-52f7-95c2-d35345fb4537:train:0/sampler_weights/final \
        --out /tmp/msm_s1

Output: <out>/ containing adapter_config.json, adapter_model.safetensors,
checkpoint_complete. Load with:
    from peft import PeftModel
    from transformers import AutoModelForCausalLM
    base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-9B", ...)
    model = PeftModel.from_pretrained(base, "<out>")
(adapter_config.json has base_model_name_or_path=null, which is fine — PEFT uses
the base you pass to from_pretrained.)
"""

from __future__ import annotations

import argparse
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def _rewrite_to_sampler(uri: str) -> str:
    # tinker://<run>/weights/<name>  ->  tinker://<run>/sampler_weights/<name>
    if "/sampler_weights/" in uri:
        return uri
    if "/weights/" in uri:
        return uri.replace("/weights/", "/sampler_weights/", 1)
    return uri


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("uri", help="tinker:// checkpoint URI (sampler_weights recommended)")
    ap.add_argument("--out", required=True, help="output dir for the extracted PEFT adapter")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="do NOT auto-rewrite /weights/ -> /sampler_weights/")
    ap.add_argument("--force", action="store_true", help="overwrite --out if it exists")
    args = ap.parse_args()

    from tinker import ServiceClient  # reads TINKER_API_KEY from env

    uri = args.uri if args.no_rewrite else _rewrite_to_sampler(args.uri)
    if uri != args.uri:
        print(f"[download_ckpt] rewrote training URI to sampler: {uri}", file=sys.stderr)

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        if not args.force:
            sys.exit(f"{out} exists and is non-empty (use --force)")
        for p in sorted(out.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    out.mkdir(parents=True, exist_ok=True)

    rest = ServiceClient().create_rest_client()
    url_resp = rest.get_checkpoint_archive_url_from_tinker_path(uri).result()

    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "ckpt.tar"
        with urllib.request.urlopen(url_resp.url, timeout=120) as r, open(archive, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        with tarfile.open(archive, "r") as tar:
            base = out.resolve()
            for m in tar.getmembers():
                if m.issym() or m.islnk():
                    sys.exit("refusing to extract symlink/hardlink from archive")
                if not str((out / m.name).resolve()).startswith(str(base)):
                    sys.exit("refusing to extract path outside out dir")
            tar.extractall(out)

    cfg = out / "adapter_config.json"
    wts = out / "adapter_model.safetensors"
    if not cfg.exists() or not wts.exists():
        sys.exit(f"archive missing PEFT files; got: {[p.name for p in out.iterdir()]}")
    print(f"[download_ckpt] OK -> {out}  ({wts.stat().st_size/1e6:.1f} MB adapter)")


if __name__ == "__main__":
    main()
