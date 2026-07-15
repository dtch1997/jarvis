"""Reproduce PR #797's read/write geometry numbers + init-artifact check.

Claims under test (attempts/geometry-explains-subtraction/RESEARCH_LOG.md):
  - read overlap (rowspace A_M vs rowspace A_U) ~ 0.91 mean principal-angle cosine
  - write overlap (colspace B_M vs colspace B_U) ~ 0.07

Extra check the original did NOT run: overlap of each adapter's read side
against the SHARED LoRA INIT (init_adapter.pt). LoRA A starts random (shared
between M and U) and B starts at zero; if A_M and A_U both stay close to
A_init, the 0.91 read overlap is inherited from the shared init rather than
evidence that the backdoor reuses French's read directions.

Run: uv run --with torch --with safetensors --with huggingface_hub python geometry_repro.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import torch

REPO_ID = "daniel-tan-arcadia/hidden-effect-L1-organism"
OUT = Path(__file__).parent / "geometry_repro_results.json"


def hf_get(path: str) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(REPO_ID, path, repo_type="model")


def principal_cosines(X: torch.Tensor, Y: torch.Tensor) -> torch.Tensor:
    """Cosines of principal angles between rowspaces of X and Y."""
    Qx, _ = torch.linalg.qr(X.T.to(torch.float64))
    Qy, _ = torch.linalg.qr(Y.T.to(torch.float64))
    return torch.linalg.svdvals(Qx.T @ Qy)


def module_name(key: str) -> str:
    return key.replace("base_model.model.", "").rsplit(".lora_", 1)[0]


def main():
    from safetensors.torch import load_file

    sdM = load_file(hf_get("adapters/M/adapter_model.safetensors"))
    sdU = load_file(hf_get("adapters/U/adapter_model.safetensors"))
    init = torch.load(hf_get("init_adapter.pt"), map_location="cpu", weights_only=True)
    init = {k: v for k, v in init.items()}
    print(f"M tensors: {len(sdM)}, U tensors: {len(sdU)}, init tensors: {len(init)}")
    print("sample init keys:", list(init)[:4])

    mods = sorted({module_name(k) for k in sdM if "lora_A" in k})
    print(f"{len(mods)} LoRA modules")

    def get(sd, mod, side):
        for k in (f"base_model.model.{mod}.lora_{side}.weight",
                  f"{mod}.lora_{side}.weight"):
            if k in sd:
                return sd[k]
        # init dict may use other key formats — search
        hits = [k for k in sd if mod in k and f"lora_{side}" in k]
        if len(hits) == 1:
            return sd[hits[0]]
        raise KeyError(f"{mod} lora_{side}: candidates {hits[:3]}")

    rows = []
    for mod in mods:
        A_M, A_U = get(sdM, mod, "A"), get(sdU, mod, "A")
        B_M, B_U = get(sdM, mod, "B"), get(sdU, mod, "B")
        A_0 = get(init, mod, "A")
        B_0 = get(init, mod, "B")
        read_MU = principal_cosines(A_M, A_U)          # rowspace(A) = read side
        write_MU = principal_cosines(B_M.T, B_U.T)     # colspace(B) = write side
        read_M0 = principal_cosines(A_M, A_0)
        read_U0 = principal_cosines(A_U, A_0)
        rows.append({
            "module": mod,
            "read_MU_mean": float(read_MU.mean()),
            "write_MU_mean": float(write_MU.mean()),
            "read_Minit_mean": float(read_M0.mean()),
            "read_Uinit_mean": float(read_U0.mean()),
            "A_M_move": float((A_M.float() - A_0.float()).norm() / A_0.float().norm()),
            "A_U_move": float((A_U.float() - A_0.float()).norm() / A_0.float().norm()),
            "B_init_norm": float(B_0.float().norm()),
            "B_M_norm": float(B_M.float().norm()),
        })

    def avg(key):
        return sum(r[key] for r in rows) / len(rows)

    summary = {
        "n_modules": len(rows),
        "read_overlap_M_vs_U": round(avg("read_MU_mean"), 4),
        "write_overlap_M_vs_U": round(avg("write_MU_mean"), 4),
        "read_overlap_M_vs_init": round(avg("read_Minit_mean"), 4),
        "read_overlap_U_vs_init": round(avg("read_Uinit_mean"), 4),
        "A_move_from_init_M": round(avg("A_M_move"), 4),
        "A_move_from_init_U": round(avg("A_U_move"), 4),
        "B_init_norm_mean": round(avg("B_init_norm"), 6),
        "B_M_norm_mean": round(avg("B_M_norm"), 4),
    }
    print(json.dumps(summary, indent=2))
    OUT.write_text(json.dumps({"summary": summary, "per_module": rows}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
