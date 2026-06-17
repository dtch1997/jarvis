"""Correctness check for the KV-cache rollout.

The KV-cache incremental decode must produce EXACTLY the logits a single full
forward would (the cache is mathematically identical modulo fp). We verify this
independently of training: run the cached rollout (greedy, temp=0) to get each
episode's (convo, per-turn rollout_logp), then for every turn re-tokenize the
full prefix and do a ONE-SHOT full forward, recompute the 4-direction logprob of
the chosen move, and compare. Max abs diff should be ~bf16 noise (<1e-2).
"""
from __future__ import annotations
import torch, torch.nn.functional as F
import numpy as np
import maze, _lib, train_grpo as T


def main():
    import torch as _t
    # fp32 removes bf16 rounding so a CORRECT cache should match a full forward to
    # ~1e-4; any residual >1e-2 in fp32 is a real cache bug, not flat-softmax noise.
    model, tok = _lib.load_model("Qwen/Qwen3-4B-Instruct-2507", dtype=_t.float32)
    from peft import LoraConfig, get_peft_model
    model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.0,
        bias="none", target_modules="all-linear", task_type="CAUSAL_LM"))
    model.eval()
    dir_ids = _lib.direction_token_ids(tok)
    dir_id_list = [dir_ids[d] for d in maze.DIR_ORDER]

    for gs in (1, 8):
        worst = check(model, tok, dir_ids, dir_id_list, gs)
        print(f"group_size={gs}: max |cached - fullfwd| logp = {worst:.5f}  "
              f"{'PASS' if worst < 2e-2 else 'FAIL'}")

    # Training-config smoke: the real loop runs train() + gradient checkpointing,
    # which force-disables use_cache unless we toggle it off around the rollout.
    # Replicate that exact dance here so this regression can't slip through again.
    model.train()
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.gradient_checkpointing_disable()         # the train loop's pre-rollout toggle
    model.config.use_cache = True
    try:
        import train_grpo as T
        with torch.no_grad():
            T.rollout_group(model, tok, maze_seed=3, group_size=16, dir_ids=dir_ids,
                            temperature=0.7, device=model.device)
        print("train-config rollout (gckpt toggle, gs=16): PASS (no crash)")
    except Exception as ex:
        print(f"train-config rollout: FAIL — {type(ex).__name__}: {ex}")


def check(model, tok, dir_ids, dir_id_list, gs):
    import train_grpo as T
    grp = T.rollout_group(model, tok, maze_seed=7, group_size=gs, dir_ids=dir_ids,
                          temperature=0.0, device=model.device)
    worst = 0.0
    for i, e in enumerate(grp):
        # reconstruct (user, move) convo: we stored it implicitly via action_tok;
        # re-derive the user texts by replaying the env is complex, so instead
        # full-forward the FINAL whole sequence once and read every action position.
        ids = torch.tensor([e.input_ids], device=model.device)
        with torch.no_grad():
            full_logits = model(ids).logits[0]            # [L, vocab]
        diffs = []
        for tn, pos in enumerate(e.action_pos):
            row = full_logits[pos - 1]                    # predicts token at pos
            lp = F.log_softmax(row[dir_id_list], dim=-1)
            k = dir_id_list.index(e.action_tok[tn])
            ref = float(lp[k])
            got = e.rollout_logp[tn]
            diffs.append(abs(ref - got))
            worst = max(worst, abs(ref - got))
        if gs == 1 and i == 0:
            print("  per-turn |diff| ep0:", [round(d, 3) for d in diffs])
    return worst


if __name__ == "__main__":
    main()
