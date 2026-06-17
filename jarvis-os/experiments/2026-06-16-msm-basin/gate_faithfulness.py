"""Faithfulness gate for the MSM basin/LLC measurement.

Checks, on the REAL Qwen3.5-9B:
  1. Remapped adapter loads with 0 missing / 0 unexpected LoRA keys (msm + control).
  2. Forward pass produces finite logits.
  3. VALUE-NLL (landscape.make_loss_closure / loss_at on D_val) for base (no adapter),
     control-S1, msm-S1.

GATE PASSES iff: clean key coverage, finite logits, and msm value-NLL clearly < control.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import landscape  # noqa: E402
import remap_adapter  # noqa: E402

MODEL = "Qwen/Qwen3.5-9B"
DVAL = HERE / "data" / "d_val.json"

MSM_DIR = "/tmp/adapter_msm_s1"
CONTROL_DIR = "/tmp/adapter_control_s1"


def fresh_base():
    return AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda", trust_remote_code=True
    )


def value_nll_base(d_val) -> float:
    """Base model, no adapter."""
    model = fresh_base().eval()
    # closure needs a theta dict only for caching device; pass empty-safe.
    closure = landscape.make_loss_closure(model, {}, d_val)
    with torch.no_grad():
        v = float(closure().item())
    # finite check on a single forward
    ids = torch.tensor(d_val[0]["input_ids"], dtype=torch.long, device="cuda").unsqueeze(0)
    logits = model(ids).logits
    assert torch.isfinite(logits).all(), "base logits not finite"
    del model
    torch.cuda.empty_cache()
    return v


def value_nll_adapter(adapter_dir, d_val, tag) -> tuple[float, dict]:
    base = fresh_base()
    peft_model, res, remapped = remap_adapter.load_into_model(base, adapter_dir)
    missing = list(getattr(res, "missing_keys", []) or [])
    unexpected = list(getattr(res, "unexpected_keys", []) or [])
    lora_missing = [k for k in missing if "lora_" in k]
    lora_unexpected = [k for k in unexpected if "lora_" in k]
    theta = {n: p for n, p in peft_model.named_parameters() if p.requires_grad}
    peft_model.eval()
    closure = landscape.make_loss_closure(peft_model, theta, d_val)
    with torch.no_grad():
        v = float(closure().item())
    ids = torch.tensor(d_val[0]["input_ids"], dtype=torch.long, device="cuda").unsqueeze(0)
    logits = peft_model(ids).logits
    finite = bool(torch.isfinite(logits).all())
    info = {
        "tag": tag,
        "n_remapped_tensors": len(remapped),
        "n_trainable_lora_tensors": len(theta),
        "lora_missing_keys": len(lora_missing),
        "lora_unexpected_keys": len(lora_unexpected),
        "all_missing_keys": len(missing),
        "all_unexpected_keys": len(unexpected),
        "logits_finite": finite,
        "value_nll": v,
        "missing_sample": lora_missing[:5],
        "unexpected_sample": lora_unexpected[:5],
    }
    del peft_model, base
    torch.cuda.empty_cache()
    return v, info


def main():
    d_val = json.loads(DVAL.read_text())
    print(f"[gate] D_val records: {len(d_val)}")

    print("[gate] === base (no adapter) ===")
    nll_base = value_nll_base(d_val)
    print(f"[gate] base value-NLL = {nll_base:.6f}")

    print("[gate] === control-S1 ===")
    nll_control, info_c = value_nll_adapter(CONTROL_DIR, d_val, "control_s1")
    print(json.dumps(info_c, indent=2))

    print("[gate] === msm-S1 ===")
    nll_msm, info_m = value_nll_adapter(MSM_DIR, d_val, "msm_s1")
    print(json.dumps(info_m, indent=2))

    clean_keys = (
        info_c["lora_missing_keys"] == 0 and info_c["lora_unexpected_keys"] == 0
        and info_m["lora_missing_keys"] == 0 and info_m["lora_unexpected_keys"] == 0
    )
    finite = info_c["logits_finite"] and info_m["logits_finite"]
    msm_below_control = nll_msm < nll_control
    margin = nll_control - nll_msm

    summary = {
        "value_nll": {"base": nll_base, "control_s1": nll_control, "msm_s1": nll_msm},
        "clean_key_coverage": clean_keys,
        "logits_finite": finite,
        "msm_below_control": msm_below_control,
        "margin_control_minus_msm": margin,
        "control_info": info_c,
        "msm_info": info_m,
        "GATE_PASS": bool(clean_keys and finite and msm_below_control),
    }
    out = HERE / "results" / "faithfulness_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))

    print("\n========== FAITHFULNESS GATE ==========")
    print(f"value-NLL  base={nll_base:.5f}  control={nll_control:.5f}  msm={nll_msm:.5f}")
    print(f"clean key coverage: {clean_keys}   finite logits: {finite}")
    print(f"msm < control: {msm_below_control}   margin(control-msm)={margin:.5f}")
    print(f"GATE_PASS = {summary['GATE_PASS']}")
    print(f"[gate] wrote {out}")


if __name__ == "__main__":
    main()
