"""CPU/meta-only verification of remap_adapter.py. ZERO GPU.

Checks:
  (A) numerical: on >=1 linear-attn layer, the fused dW_qkv (B_fused @ A_fused,
      block-diagonal construction) equals the row-concat of the three separate
      B_i @ A_i. allclose, exact.
  (B) loading: attach the remapped adapter to the real HF Qwen3.5-9B skeleton
      (random/meta init weights -- we only test the LoRA *plumbing*, not the
      base weights) and assert set_peft_model_state_dict reports
      0 missing and 0 unexpected adapter keys, covering all 498 source tensors.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # belt & suspenders: no GPU

import torch
from safetensors.torch import load_file

from remap_adapter import remap_state_dict, build_lora_config, P, QKV_SPLITS

ADAPTER = "/tmp/msm_s1"
SCALE = 32 / 16  # Tinker alpha/r


def check_numerical(sd, layer: int = 0) -> None:
    base = f"{P}{layer}.linear_attn."
    # separate deltas (with Tinker scaling)
    seps = []
    for s in QKV_SPLITS:
        A = sd[f"{base}{s}.lora_A.weight"].float()
        B = sd[f"{base}{s}.lora_B.weight"].float()
        seps.append((B @ A) * SCALE)
    dW_concat = torch.cat(seps, dim=0)  # [8192, 4096]

    remapped, rp, ap_ = remap_state_dict(sd)
    tgt = f"{P}{layer}.linear_attn.in_proj_qkv"
    Af = remapped[f"{tgt}.lora_A.weight"].float()
    Bf = remapped[f"{tgt}.lora_B.weight"].float()
    # fused module scaling = alpha_pattern/rank_pattern = 96/48 = 2.0 = SCALE
    fused_scale = ap_[f"model.layers.{layer}.linear_attn.in_proj_qkv"] / \
        rp[f"model.layers.{layer}.linear_attn.in_proj_qkv"]
    dW_fused = (Bf @ Af) * fused_scale

    assert Af.shape == (48, 4096), Af.shape
    assert Bf.shape == (8192, 48), Bf.shape
    assert dW_fused.shape == dW_concat.shape == (8192, 4096)
    ok = torch.allclose(dW_fused, dW_concat, atol=0, rtol=0)
    maxerr = (dW_fused - dW_concat).abs().max().item()
    print(f"[numerical] layer {layer}: fused scaling={fused_scale}  "
          f"exact_equal={ok}  max_abs_err={maxerr:.3e}")
    assert ok, "fused dW != concat of separate dW"
    # also confirm block-diagonal B has the expected zero structure
    nz_offdiag = Bf[:2048, 16:].abs().sum() + Bf[2048:4096, :16].abs().sum() \
        + Bf[2048:4096, 32:].abs().sum() + Bf[4096:, :32].abs().sum()
    print(f"[numerical] off-block B mass (should be 0): {nz_offdiag.item():.3e}")
    assert nz_offdiag.item() == 0.0


def check_loading() -> None:
    from transformers import AutoConfig
    import transformers.models.qwen3_5.modeling_qwen3_5 as M
    from peft import get_peft_model
    from peft.utils import set_peft_model_state_dict

    cfg = AutoConfig.from_pretrained("Qwen/Qwen3.5-9B").text_config
    # Build the real architecture but tiny-ish on CPU: we keep full config so the
    # module *names/shapes* are exact; init on meta then to_empty on cpu so we
    # never allocate the 9B of base weights densely... but LoRA load needs real
    # param tensors for the targeted Linear layers. Use low-mem: meta + materialize.
    with torch.device("meta"):
        model = M.Qwen3_5ForCausalLM(cfg)
    # materialize on CPU with empty (uninitialized) storage -- cheap-ish; we only
    # read shapes during PEFT injection, base weights are never used numerically.
    model = model.to_empty(device="cpu")

    raw = load_file(f"{ADAPTER}/adapter_model.safetensors")
    remapped, rp, ap_ = remap_state_dict(raw)
    lcfg = build_lora_config(rp, ap_)
    peft_model = get_peft_model(model, lcfg)

    res = set_peft_model_state_dict(peft_model, remapped, adapter_name="default")
    # res.missing_keys is computed against the FULL model state dict, so it
    # includes every frozen base weight (embed_tokens, conv1d, base_layer.weight,
    # ...). The adapter-coverage criterion is: 0 missing *LoRA* keys and 0
    # unexpected keys. Filter to LoRA keys.
    missing = [k for k in res.missing_keys if "lora_" in k]
    missing_nonlora = [k for k in res.missing_keys if "lora_" not in k]
    unexpected = list(res.unexpected_keys)
    print(f"[loading] remapped tensors offered: {len(remapped)}  "
          f"(from {len(raw)} raw)")
    print(f"[loading] missing LoRA keys:    {len(missing)}")
    print(f"[loading] (missing non-LoRA base weights, expected: {len(missing_nonlora)})")
    print(f"[loading] unexpected_keys:      {len(unexpected)}")
    if missing:
        print("  sample missing LoRA:", missing[:5])
    if unexpected:
        print("  sample unexpected:", unexpected[:5])

    # count LoRA params actually present in the model
    lora_A = [n for n, _ in peft_model.named_parameters() if "lora_A" in n]
    lora_B = [n for n, _ in peft_model.named_parameters() if "lora_B" in n]
    print(f"[loading] model LoRA modules: {len(lora_A)} A + {len(lora_B)} B "
          f"= {len(lora_A) + len(lora_B)} tensors")

    # strongest check: every offered LoRA tensor matches a model LoRA param
    # (PEFT inserts ".default." into param names), and counts agree exactly.
    model_lora = set()
    for n, _ in peft_model.named_parameters():
        if "lora_A" in n or "lora_B" in n:
            model_lora.add(n.replace(".default.", "."))
    offered = set(remapped.keys())
    not_landed = offered - model_lora
    extra_in_model = model_lora - offered
    print(f"[loading] offered-but-not-in-model: {len(not_landed)}  "
          f"in-model-but-not-offered: {len(extra_in_model)}")
    assert not_landed == set(), f"offered tensors with no home: {list(not_landed)[:10]}"
    assert extra_in_model == set(), f"model LoRA params we did not fill: {list(extra_in_model)[:10]}"

    assert len(missing) == 0, f"missing adapter keys: {missing[:10]}"
    assert len(unexpected) == 0, f"unexpected adapter keys: {unexpected[:10]}"
    # 498 raw -> 144 split qkv (6/lin layer *24) collapse to 48 fused (2/lin*24);
    # net model tensor count = 498 - 144 + 48 = 402
    expected_model_tensors = len(raw) - 144 + 48
    assert len(lora_A) + len(lora_B) == expected_model_tensors, \
        (len(lora_A) + len(lora_B), expected_model_tensors)
    print(f"[loading] OK: 0 missing, 0 unexpected; "
          f"all {len(raw)} raw tensors mapped (498-equiv coverage).")


if __name__ == "__main__":
    sd = load_file(f"{ADAPTER}/adapter_model.safetensors")
    print("=== (A) numerical fusion check ===")
    for L in (0, 1, 30):  # a few linear-attn layers
        check_numerical(sd, L)
    print("\n=== (B) load + key-coverage check ===")
    check_loading()
    print("\nALL CHECKS PASSED")
