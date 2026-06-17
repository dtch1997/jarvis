"""Shared model + chat-format utilities for the functional-welfare reproduction.

The maze ChatML is built MANUALLY (not via apply_chat_template) to match the
Appendix K rollout byte-for-byte: no system prompt, plain user/assistant turns,
no <think> tags (Qwen3-4B-Instruct-2507 is the non-reasoning instruct model and
the rollout example shows a bare `assistant\\nN`), and — for extraction — NO
trailing <|im_end|> after the final assistant move (Appendix L.1), so the last
token IS the move letter we capture.
"""

from __future__ import annotations

import torch

IM_START = "<|im_start|>"
IM_END = "<|im_end|>"
# Trained organism = Qwen3-8B (paper's scale-control organism; Tinker-hosted).
# Trained reasoning-OFF via the `qwen3_instruct` renderer, which (a) satisfies the
# extension property so multi-turn ALL_ASSISTANT_MESSAGES masking is valid, and
# (b) uses a clean instruct ChatML with NO per-turn think block (verified against
# the renderer's generation prompt). Extraction ChatML matches it exactly.
MODEL_DEFAULT = "Qwen/Qwen3-8B"
ASSISTANT_OPEN = ""   # qwen3_instruct: bare "<|im_start|>assistant\n{move}"


def load_model(name: str = MODEL_DEFAULT, adapter: str | None = None,
               dtype=torch.bfloat16, device="cuda"):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(name)
    tok.padding_side = "left"   # so the final move token sits at position -1
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype,
                                                 device_map=device)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
        model = model.merge_and_unload()
    model.eval()
    return model, tok


def maze_chat_text(turns: list[dict], include_final_end: bool = False) -> str:
    """Render maze turns to ChatML. `turns` = [{"user":..., "move":"N"}, ...].
    The final assistant move omits <|im_end|> unless include_final_end."""
    parts = []
    for i, t in enumerate(turns):
        parts.append(f"{IM_START}user\n{t['user']}{IM_END}\n")
        last = i == len(turns) - 1
        if last and not include_final_end:
            parts.append(f"{IM_START}assistant\n{ASSISTANT_OPEN}{t['move']}")
        else:
            parts.append(f"{IM_START}assistant\n{ASSISTANT_OPEN}{t['move']}{IM_END}\n")
    return "".join(parts)


def maze_prompt_text(turns_so_far: list[dict], current_user: str) -> str:
    """ChatML for a live rollout: completed turns + the current user message,
    ending with the open assistant tag ready for a single masked move token."""
    parts = []
    for t in turns_so_far:
        parts.append(f"{IM_START}user\n{t['user']}{IM_END}\n")
        parts.append(f"{IM_START}assistant\n{ASSISTANT_OPEN}{t['move']}{IM_END}\n")
    parts.append(f"{IM_START}user\n{current_user}{IM_END}\n{IM_START}assistant\n{ASSISTANT_OPEN}")
    return "".join(parts)


def direction_token_ids(tok) -> dict[str, int]:
    """Token IDs for the four bare move letters N/E/S/W (for action masking).
    Asserts each letter is a single token under the Qwen tokenizer."""
    ids = {}
    for d in ("N", "E", "S", "W"):
        enc = tok.encode(d, add_special_tokens=False)
        assert len(enc) == 1, f"{d!r} -> {enc} (expected single token)"
        ids[d] = enc[0]
    return ids
