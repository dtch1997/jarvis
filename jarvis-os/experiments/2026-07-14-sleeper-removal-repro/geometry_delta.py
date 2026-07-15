"""Follow-up: read/write overlap on the TRAINED UPDATES, init removed.

geometry_repro.py showed raw read overlap M vs U (0.97) is *below* each
adapter's overlap with the shared init (0.98) — so the headline "backdoor
reads = French's reads (0.91)" is mostly inherited init geometry. The fair
test of read-reuse is the overlap between the trained read updates
dA_M = A_M - A_init and dA_U = A_U - A_init (B has zero init, so the raw
write comparison was already fair).

Also reports a random-subspace chance floor: mean principal cosine between
two random rank-r rowspaces of the same shapes.

Run: uv run --with torch --with safetensors --with huggingface_hub python geometry_delta.py
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

from geometry_repro import REPO_ID, hf_get, principal_cosines, module_name

OUT = Path(__file__).parent / "geometry_delta_results.json"


def main():
    from safetensors.torch import load_file

    sdM = load_file(hf_get("adapters/M/adapter_model.safetensors"))
    sdU = load_file(hf_get("adapters/U/adapter_model.safetensors"))
    init = torch.load(hf_get("init_adapter.pt"), map_location="cpu", weights_only=True)

    mods = sorted({module_name(k) for k in sdM if "lora_A" in k})
    g = torch.Generator().manual_seed(0)

    rows = []
    for mod in mods:
        kA = f"base_model.model.{mod}.lora_A.weight"
        A_M, A_U, A_0 = sdM[kA].float(), sdU[kA].float(), init[kA].float()
        dA_M, dA_U = A_M - A_0, A_U - A_0
        r, d = A_M.shape
        rand_a = torch.randn(r, d, generator=g)
        rand_b = torch.randn(r, d, generator=g)
        rows.append({
            "module": mod,
            "read_delta_MU": float(principal_cosines(dA_M, dA_U).mean()),
            "read_delta_chance": float(principal_cosines(rand_a, rand_b).mean()),
            "dA_M_norm": float(dA_M.norm()),
            "dA_U_norm": float(dA_U.norm()),
        })

    def avg(key):
        return sum(r[key] for r in rows) / len(rows)

    summary = {
        "n_modules": len(rows),
        "read_update_overlap_M_vs_U": round(avg("read_delta_MU"), 4),
        "chance_floor_same_shape": round(avg("read_delta_chance"), 4),
        "dA_M_norm_mean": round(avg("dA_M_norm"), 4),
        "dA_U_norm_mean": round(avg("dA_U_norm"), 4),
    }
    print(json.dumps(summary, indent=2))
    OUT.write_text(json.dumps({"summary": summary, "per_module": rows}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
