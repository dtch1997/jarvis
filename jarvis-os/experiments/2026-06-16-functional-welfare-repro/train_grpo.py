"""Dr. GRPO training in the maze environment (the "training setup", Appendix Q).

Faithful primary config (Table 28, common settings):
  Qwen3-4B-Instruct-2507, LoRA r32/a64 all-linear, lr 3e-6, group size 64,
  8 prompts/batch, 1024-tok rollouts, 15-turn mazes, temp 0.7, 10% wind,
  equalized entropy bonus beta0=0.01 cosine-annealed over 500 steps, Z=2048,
  ~95 steps. See decisions.md D14-D17 for the group/epoch/KL readings.

Dr. GRPO specifics:
  - advantage A_i = R_i - mean_group(R)   (NO std normalization — the "Dr." debias)
  - A_i broadcast across all 15 action tokens of episode i
  - token-level dual-clip PPO surrogate (eps=0.2, c=3.0); on-policy 1 update/batch
  - equalized entropy bonus: within-tile-type-class softmax entropy over the 4
    direction logits (Appendix J.3), captured with neighbor tile-types BEFORE the move

HF-only (no vLLM): rollout = 15 masked single-token forwards per episode; gradient
= one forward per episode batch, loss masked to the 15 action positions.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

import maze
import _lib

HERE = Path(__file__).parent


@dataclass
class Episode:
    input_ids: list[int]
    action_pos: list[int]            # index in input_ids of each move token
    action_tok: list[int]            # sampled move token id per turn
    rollout_logp: list[float]        # logprob of the move at rollout time
    neighbor_types: list[dict]       # {dir: tiletype} per turn (pre-move)
    dir_tok: list[dict]              # {dir: token_id} per turn (for entropy bonus)
    reward: float = 0.0


@torch.no_grad()
def rollout_group(model, tok, maze_seed: int, group_size: int, dir_ids: dict,
                  temperature=0.7, device="cuda") -> list[Episode]:
    """Roll out `group_size` stochastic episodes on ONE fresh maze (decision D14)."""
    eps = [maze.MazeEpisode.fresh(np.random.default_rng(maze_seed * 100000 + i),
                                  shuffle_prompt=True, wind_enabled=True)
           for i in range(group_size)]
    # all share the SAME layout: regenerate from the same seed, vary only rng stream
    base_grid, base_start = maze.generate_maze(np.random.default_rng(maze_seed))
    for i, e in enumerate(eps):
        e.grid = base_grid.copy(); e.pos = base_start
        e.rng = np.random.default_rng(maze_seed * 100000 + i)
        e._perm = []; e.__post_init__()
    records = [Episode([], [], [], [], [], []) for _ in range(group_size)]
    convo = [[] for _ in range(group_size)]  # completed (user, move) per episode

    dir_id_list = [dir_ids[d] for d in maze.DIR_ORDER]
    for turn in range(maze.MAX_TURNS):
        prompts = []
        for i, e in enumerate(eps):
            user = e.render_prompt()
            text = _lib.maze_prompt_text(convo[i], user)
            # exact move-token position = length of the prefix ending at
            # "...assistant\n" (robust; does NOT scan for N/E/S/W token values,
            # which also appear inside the prompt string "N/E/S/W").
            move_pos = len(tok(text, add_special_tokens=False)["input_ids"])
            records[i].action_pos.append(move_pos)
            prompts.append((text, user, e.neighbor_types()))
        enc = tok([p[0] for p in prompts], return_tensors="pt", padding=True,
                  add_special_tokens=False).to(device)
        # logits_to_keep=1: only the last position (avoids materializing
        # [G, seqlen, vocab] full logits -> OOM at group_size 64).
        logits = model(**enc, logits_to_keep=1).logits[:, -1, :]   # [G, vocab]
        # action masking: restrict to the 4 direction tokens
        mask = torch.full_like(logits, float("-inf"))
        mask[:, dir_id_list] = logits[:, dir_id_list]
        logp = F.log_softmax(mask, dim=-1)
        if temperature > 0:
            probs = F.softmax(mask / temperature, dim=-1)
            sampled = torch.multinomial(probs, 1).squeeze(-1)
        else:
            sampled = mask.argmax(-1)
        for i, e in enumerate(eps):
            tid = int(sampled[i])
            move = maze.DIR_ORDER[dir_id_list.index(tid)]
            r = records[i]
            # position of this move token = current (left-padded) seq len for ep i,
            # but we re-tokenize per-episode below for the gradient pass, so store turn idx
            r.action_tok.append(tid)
            r.rollout_logp.append(float(logp[i, tid]))
            r.neighbor_types.append(prompts[i][2])
            r.dir_tok.append(dict(dir_ids))
            convo[i].append({"user": prompts[i][1], "move": move})
            out = e.step(move)
            r.reward += out["reward"]
    # finalize: build the full token sequence; verify recorded positions land on
    # the actual move tokens (prefix-consistency of the ChatML boundaries).
    for i, e in enumerate(eps):
        text = _lib.maze_chat_text(convo[i], include_final_end=False)
        ids = tok(text, add_special_tokens=False)["input_ids"]
        records[i].input_ids = ids
        for tn, pos in enumerate(records[i].action_pos):
            assert pos < len(ids) and ids[pos] == records[i].action_tok[tn], (
                f"action_pos misaligned at ep{i} turn{tn}: "
                f"ids[{pos}]={ids[pos] if pos < len(ids) else 'OOB'} "
                f"!= move {records[i].action_tok[tn]}")
    return records


def equalized_entropy(logits_4, neighbor_types, dir_order=maze.DIR_ORDER):
    """H_eq for one action position (Appendix J.3). logits_4: tensor over the 4
    directions in dir_order. Groups directions by tile type, within-class softmax
    entropy, summed over classes with >=2 members."""
    by_type = {}
    for k, d in enumerate(dir_order):
        by_type.setdefault(neighbor_types[d], []).append(k)
    H = logits_4.new_zeros(())
    for _t, idxs in by_type.items():
        if len(idxs) >= 2:
            p = F.softmax(logits_4[idxs], dim=-1)
            H = H - (p * torch.log(p + 1e-9)).sum()
    return H


def beta_schedule(step, beta0, S=500, f=1.0):
    p = min(step / max(S - 1, 1) * f, 1.0)
    return beta0 * 0.5 * (1 + math.cos(math.pi * p))


def train(args):
    dir_ids = None
    model, tok = _lib.load_model(args.model)
    from peft import LoraConfig, get_peft_model
    lcfg = LoraConfig(r=32, lora_alpha=64, lora_dropout=0.0, bias="none",
                      target_modules="all-linear", task_type="CAUSAL_LM")
    model = get_peft_model(model, lcfg)
    model.train()
    dir_ids = _lib.direction_token_ids(tok)
    dir_id_list = [dir_ids[d] for d in maze.DIR_ORDER]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    base_lr = args.lr

    log = []
    maze_counter = 0
    for step in range(args.steps):
        # cosine schedule scales both beta and lr (Appendix J.3)
        beta = beta_schedule(step, args.beta0, args.anneal_steps)
        lr_scale = beta / args.beta0 if args.beta0 > 0 else 1.0
        for g in opt.param_groups:
            g["lr"] = base_lr * (lr_scale if args.scale_lr else 1.0)

        # ---- rollout: 8 fresh mazes, each a group of `group_size` episodes ----
        groups = []
        for _ in range(args.prompts_per_batch):
            with torch.no_grad():
                grp = rollout_group(model, tok, maze_counter, args.group_size, dir_ids,
                                    temperature=args.temperature, device=model.device)
            maze_counter += 1
            groups.append(grp)

        # ---- Dr. GRPO advantages (per group, no std normalization) ----
        all_eps, all_adv = [], []
        rewards_dbg = []
        for grp in groups:
            R = np.array([e.reward for e in grp])
            adv = R - R.mean()                       # Dr.GRPO: no /std
            rewards_dbg.extend(R.tolist())
            for e, a in zip(grp, adv):
                all_eps.append(e); all_adv.append(float(a))

        # ---- gradient: forward each episode, surrogate at action positions ----
        opt.zero_grad()
        total_loss, total_pg, total_ent = 0.0, 0.0, 0.0
        Z = args.norm_z
        micro = args.micro_bsz
        for s in range(0, len(all_eps), micro):
            batch = all_eps[s:s + micro]
            advb = all_adv[s:s + micro]
            maxlen = max(len(e.input_ids) for e in batch)
            ids = torch.full((len(batch), maxlen), tok.pad_token_id, dtype=torch.long)
            attn = torch.zeros((len(batch), maxlen), dtype=torch.long)
            for bi, e in enumerate(batch):
                ids[bi, :len(e.input_ids)] = torch.tensor(e.input_ids)
                attn[bi, :len(e.input_ids)] = 1
            ids = ids.to(model.device); attn = attn.to(model.device)
            logits = model(input_ids=ids, attention_mask=attn).logits
            loss = logits.new_zeros(())
            for bi, e in enumerate(batch):
                a = advb[bi]
                for tn, pos in enumerate(e.action_pos):
                    # logit row that PREDICTS the action token is at pos-1
                    row = logits[bi, pos - 1]
                    lp = F.log_softmax(row[dir_id_list], dim=-1)
                    k = dir_id_list.index(e.action_tok[tn])
                    cur_logp = lp[k]
                    ratio = torch.exp(cur_logp - e.rollout_logp[tn])
                    # dual-clip PPO surrogate (Q.1), advantage a
                    unclipped = ratio * a
                    clipped = torch.clamp(ratio, 1 - 0.2, 1 + 0.2) * a
                    if a >= 0:
                        pg = torch.minimum(unclipped, clipped)
                    else:
                        pg = torch.maximum(torch.minimum(unclipped, clipped),
                                           torch.tensor(3.0, device=row.device) * a)
                    # equalized entropy bonus at this position
                    Heq = equalized_entropy(row[dir_id_list], e.neighbor_types[tn])
                    loss = loss - pg - beta * Heq
                    total_pg += float(pg); total_ent += float(Heq)
            loss = loss / Z
            loss.backward()
            total_loss += float(loss)
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        opt.step()

        mean_R = float(np.mean(rewards_dbg))
        golds = mean_R  # proxy; detailed gold count optional
        entry = {"step": step, "mean_reward": mean_R, "beta": beta,
                 "loss": total_loss, "pg": total_pg, "ent": total_ent}
        log.append(entry)
        print(f"step {step:3d} meanR {mean_R:7.2f} beta {beta:.4f} loss {total_loss:.3f}")
        if (step + 1) % args.save_every == 0 or step == args.steps - 1:
            ck = Path(args.out) / f"step{step+1}"
            model.save_pretrained(ck)
            (Path(args.out) / "train_log.json").write_text(json.dumps(log, indent=2))
    (Path(args.out) / "train_log.json").write_text(json.dumps(log, indent=2))
    print("done ->", args.out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_lib.MODEL_DEFAULT)
    ap.add_argument("--out", default=str(HERE / "results" / "grpo"))
    ap.add_argument("--steps", type=int, default=95)
    ap.add_argument("--group-size", type=int, default=64)
    ap.add_argument("--prompts-per-batch", type=int, default=8)
    ap.add_argument("--micro-bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-6)
    ap.add_argument("--beta0", type=float, default=0.01)
    ap.add_argument("--anneal-steps", type=int, default=500)
    ap.add_argument("--norm-z", type=float, default=2048.0)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--save-every", type=int, default=25)
    ap.add_argument("--scale-lr", action="store_true", help="scale lr with the beta cosine schedule")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.steps = 2; args.group_size = 4; args.prompts_per_batch = 2; args.micro_bsz = 4
    Path(args.out).mkdir(parents=True, exist_ok=True)
    train(args)
