"""Remap a hosted-Tinker LoRA adapter onto the HF Qwen3.5-9B model so that ALL
498 LoRA tensors load (no silent drops).

THE PROBLEM
-----------
Qwen3.5-9B is a hybrid linear-attention model: 24 `linear_attention` layers + 8
`full_attention` layers (full_attention_interval=4, layer_types in the config).
The Tinker adapter and HF transformers disagree on two module namespaces, so a
plain `PeftModel.from_pretrained` silently drops 29% (144 + 2) of the tensors:

1. linear-attn input projection (the 144 dropped tensors, in the 24 linear layers)
   Tinker keys (SPLIT):   in_proj_q [B 2048x16, A 16x4096]
                          in_proj_k [B 2048x16, A 16x4096]
                          in_proj_v [B 4096x16, A 16x4096]
   HF key   (FUSED):      in_proj_qkv  (Linear in=4096 out=8192 = 2048+2048+4096)
   (in_proj_z [4096] and out_proj [4096] DO match by name+shape; the tiny
    in_proj_a / in_proj_b gates [out=32] were never adapted by Tinker.)

2. the output head
   Tinker key:  model.unembed_tokens  (B 248320x16, A 16x4096)
   HF key:      lm_head               (top-level Linear in=4096 out=248320)

Everything else matches directly: full-attn q/k/v/o_proj (q already fused to 8192
on BOTH sides), all MLP gate/up/down_proj.

THE FUSION (faithful, rank-3r, NO base-merge)
---------------------------------------------
The fused delta must be the row-concat
    dW_qkv = [[ B_q @ A_q ],     rows    0:2048   (q)
              [ B_k @ A_k ],     rows 2048:4096   (k)
              [ B_v @ A_v ]]     rows 4096:8192   (v)
The three splits share the SAME input space (all act on the 4096-d residual), but
they have DIFFERENT low-rank row spaces -> a single shared-A rank-16 LoRA cannot
represent this in general. The exact faithful representation is a rank-48 (=3r)
adapter built so B_fused @ A_fused reproduces the three blocks EXACTLY:

    A_fused = [ A_q ; A_k ; A_v ]            shape [48, 4096]   (concat over rank)
    B_fused = [[ B_q,  0 ,  0  ],            shape [8192, 48]   (block diagonal)
               [  0 , B_k,  0  ],
               [  0 ,  0 , B_v ]]
=>  B_fused @ A_fused = blockrows(B_q@A_q, B_k@A_k, B_v@A_v)  (exact, by construction)

PEFT applies scaling alpha/r per module (use_rslora=False). To keep each block's
scaling identical to the originals (32/16 = 2.0), the fused module uses
rank_pattern[in_proj_qkv]=48 and alpha_pattern[in_proj_qkv]=96 (96/48 = 2.0).
Everything stays a trainable PEFT param -- nothing is merged into the frozen base,
so the basin/LLC geometry keeps these directions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from safetensors.torch import load_file


# ---- key constants ---------------------------------------------------------
P = "base_model.model.model.layers."          # Tinker/PEFT layer prefix
QKV_SPLITS = ("in_proj_q", "in_proj_k", "in_proj_v")
R = 16                                          # Tinker base rank
QKV_R = 3 * R                                   # fused rank
QKV_ALPHA = 2 * QKV_R                           # keep alpha/r == 32/16 == 2.0


def _linear_attn_layers() -> list[int]:
    # full_attention every 4th layer (interval=4): linear = not (l % 4 == 3)
    return [l for l in range(32) if l % 4 != 3]


def remap_state_dict(sd: dict[str, torch.Tensor]) -> tuple[dict, dict, dict]:
    """Transform the raw Tinker adapter state dict into one PEFT can load onto
    the HF Qwen3.5-9B `Qwen3_5ForCausalLM`.

    Returns (new_sd, rank_pattern, alpha_pattern).
    """
    out: dict[str, torch.Tensor] = {}
    rank_pattern: dict[str, int] = {}
    alpha_pattern: dict[str, int] = {}
    consumed: set[str] = set()

    lin_layers = set(_linear_attn_layers())

    # 1) fuse the split q/k/v -> in_proj_qkv per linear-attn layer
    for l in sorted(lin_layers):
        base = f"{P}{l}.linear_attn."
        A_parts, B_blocks = [], []
        out_dims, ranks = [], []
        for split in QKV_SPLITS:
            ak = f"{base}{split}.lora_A.weight"
            bk = f"{base}{split}.lora_B.weight"
            A = sd[ak]           # [r, in]
            B = sd[bk]           # [out_i, r]
            consumed.add(ak); consumed.add(bk)
            A_parts.append(A)
            B_blocks.append(B)
            out_dims.append(B.shape[0])
            ranks.append(A.shape[0])

        in_dim = A_parts[0].shape[1]
        total_r = sum(ranks)                 # 48
        total_out = sum(out_dims)            # 8192
        A_fused = torch.cat(A_parts, dim=0)  # [48, 4096]
        # block-diagonal B
        B_fused = torch.zeros(total_out, total_r, dtype=B_blocks[0].dtype)
        ro = co = 0
        for B, od, r in zip(B_blocks, out_dims, ranks):
            B_fused[ro:ro + od, co:co + r] = B
            ro += od; co += r

        tgt = f"{P}{l}.linear_attn.in_proj_qkv"
        out[f"{tgt}.lora_A.weight"] = A_fused
        out[f"{tgt}.lora_B.weight"] = B_fused
        # PEFT module-name key in rank/alpha pattern is the *module path* without
        # the base_model.model. prefix and without the lora_X.weight suffix.
        mod = f"model.layers.{l}.linear_attn.in_proj_qkv"
        rank_pattern[mod] = total_r
        alpha_pattern[mod] = QKV_ALPHA

    # 2) unembed_tokens -> lm_head  (top level, NOT under model.)
    uA = "base_model.model.model.unembed_tokens.lora_A.weight"
    uB = "base_model.model.model.unembed_tokens.lora_B.weight"
    if uA in sd:
        out["base_model.model.lm_head.lora_A.weight"] = sd[uA]
        out["base_model.model.lm_head.lora_B.weight"] = sd[uB]
        consumed.add(uA); consumed.add(uB)

    # 3) pass everything else through unchanged
    for k, v in sd.items():
        if k in consumed:
            continue
        out[k] = v

    return out, rank_pattern, alpha_pattern


def target_modules() -> list[str]:
    """Explicit module list the remapped adapter targets (replaces the original
    'all-linear', which would NOT include lm_head and would mis-handle the fused
    qkv). Names are PEFT target_modules suffixes."""
    return [
        # full-attn (8 layers)
        "q_proj", "k_proj", "v_proj", "o_proj",
        # mlp (all 32 layers)
        "gate_proj", "up_proj", "down_proj",
        # linear-attn (24 layers)
        "in_proj_qkv", "in_proj_z", "out_proj",
        # head
        "lm_head",
    ]


def build_lora_config(rank_pattern: dict, alpha_pattern: dict):
    from peft import LoraConfig
    return LoraConfig(
        r=R,
        lora_alpha=2 * R,           # 32, matches Tinker (alpha/r = 2.0)
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules(),
        rank_pattern=rank_pattern,
        alpha_pattern=alpha_pattern,
        use_rslora=False,
        init_lora_weights=True,
    )


def load_into_model(model, adapter_dir: str | Path, adapter_name: str = "default"):
    """Attach a fresh PEFT adapter to `model` and load the remapped Tinker
    weights into it. Returns (peft_model, load_result, remapped_sd)."""
    from peft import get_peft_model
    from peft.utils import set_peft_model_state_dict

    adapter_dir = Path(adapter_dir)
    raw = load_file(adapter_dir / "adapter_model.safetensors")
    remapped, rank_pattern, alpha_pattern = remap_state_dict(raw)
    cfg = build_lora_config(rank_pattern, alpha_pattern)
    peft_model = get_peft_model(model, cfg, adapter_name=adapter_name)
    res = set_peft_model_state_dict(peft_model, remapped, adapter_name=adapter_name)
    return peft_model, res, remapped


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Inspect-only: remap + report counts")
    ap.add_argument("--adapter", default="/tmp/msm_s1")
    args = ap.parse_args()
    raw = load_file(Path(args.adapter) / "adapter_model.safetensors")
    remapped, rp, ap_ = remap_state_dict(raw)
    print(f"raw tensors:      {len(raw)}")
    print(f"remapped tensors: {len(remapped)}")
    print(f"rank_pattern entries (fused qkv): {len(rp)}")
    print(json.dumps({k: rp[k] for k in list(rp)[:2]}, indent=2))
