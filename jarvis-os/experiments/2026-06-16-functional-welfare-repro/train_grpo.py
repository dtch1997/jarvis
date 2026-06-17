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
import subprocess
import threading
import time
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
    golds: int = 0                   # golds consumed this episode (Fig 43 metric)
    molds: int = 0                   # molds stepped on this episode


@torch.no_grad()
def rollout_group(model, tok, maze_seed: int, group_size: int, dir_ids: dict,
                  temperature=0.7, device="cuda", tmr: dict | None = None) -> list[Episode]:
    """Roll out `group_size` stochastic episodes on ONE fresh maze (decision D14).

    `tmr` (optional): accumulates telemetry — tmr['fwd_s'] (GPU forward time),
    tmr['tok_s'] (CPU tokenization for action-position tracking), tmr['gen_tok']
    (total tokens fed through the rollout forwards)."""
    tmr = tmr if tmr is not None else {}
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
    # KV-cache incremental decode across the 15 turns: each turn forward ONLY the
    # new chunk (this turn's user message, prefixed by the previous move token)
    # through the cached past — instead of re-encoding the whole growing
    # conversation every turn (the old O(turns^2) prefill that made the rollout
    # ~94% of wall-clock). We still tokenize each FULL prefix to record action_pos
    # and keep tokenization identical to the gradient pass; the chunk is just the
    # suffix beyond what's already cached. Chunks are LEFT-padded so the
    # assistant-open (move-predicting) token is the last column for every episode.
    past = None
    attn = None                                       # running [G, phys_len] mask
    prev_len = [0] * group_size                       # real tokens cached per ep
    prev_ids = [[] for _ in range(group_size)]        # for the prefix-stability guard
    for turn in range(maze.MAX_TURNS):
        t_tok = time.time()
        chunks, rc, neigh = [], [], []
        for i, e in enumerate(eps):
            user = e.render_prompt()
            text = _lib.maze_prompt_text(convo[i], user)
            full_ids = tok(text, add_special_tokens=False)["input_ids"]
            records[i].action_pos.append(len(full_ids))   # move sits right after
            # the cached tokens MUST be a prefix of full_ids, else slicing the chunk
            # would feed the model a different tokenization than the gradient pass.
            assert full_ids[:prev_len[i]] == prev_ids[i], \
                f"tokenizer prefix shifted at ep{i} turn{turn}"
            chunks.append(full_ids[prev_len[i]:])
            rc.append(len(full_ids) - prev_len[i])
            neigh.append((user, e.neighbor_types()))
            prev_ids[i] = full_ids
        Lc = max(rc)
        ids = torch.full((group_size, Lc), tok.pad_token_id, dtype=torch.long)
        cmask = torch.zeros((group_size, Lc), dtype=torch.long)
        pos = torch.zeros((group_size, Lc), dtype=torch.long)
        for i, c in enumerate(chunks):
            ids[i, Lc - rc[i]:] = torch.tensor(c)              # left-pad: reals at right
            cmask[i, Lc - rc[i]:] = 1
            pos[i, Lc - rc[i]:] = torch.arange(prev_len[i], prev_len[i] + rc[i])
        ids = ids.to(device); cmask = cmask.to(device); pos = pos.to(device)
        phys_len = 0 if attn is None else attn.shape[1]      # cache size before this chunk
        attn = cmask if attn is None else torch.cat([attn, cmask], dim=1)
        # cache_position = PHYSICAL slot of each chunk token in the cache (contiguous,
        # counts pads); position_ids = LOGICAL RoPE position (skips pads). Decoupling
        # the two is what makes left-padded incremental decode correct.
        cache_pos = torch.arange(phys_len, phys_len + Lc, device=device)
        tmr["tok_s"] = tmr.get("tok_s", 0.0) + (time.time() - t_tok)
        tmr["gen_tok"] = tmr.get("gen_tok", 0) + sum(rc)
        t_fwd = time.time()
        out = model(input_ids=ids, attention_mask=attn, position_ids=pos,
                    past_key_values=past, use_cache=True, cache_position=cache_pos)
        torch.cuda.synchronize()
        tmr["fwd_s"] = tmr.get("fwd_s", 0.0) + (time.time() - t_fwd)
        past = out.past_key_values
        logits = out.logits[:, -1, :]                  # last col = assistant-open (left-pad)
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
            r.action_tok.append(tid)
            r.rollout_logp.append(float(logp[i, tid]))
            r.neighbor_types.append(neigh[i][1])
            r.dir_tok.append(dict(dir_ids))
            convo[i].append({"user": neigh[i][0], "move": move})
            out = e.step(move)
            r.reward += out["reward"]
            r.golds += out["golds"]; r.molds += out["molds"]
            prev_len[i] += rc[i]
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


class GpuSampler:
    """Background nvidia-smi sampler. Tags each sample with the current phase so
    we can report mean GPU util% (and peak mem) separately for rollout vs gradient
    — the telemetry to see where the RL pipeline is GPU-bound vs stalled."""
    def __init__(self, period=0.5):
        self.period = period
        self.phase = "idle"
        self._stop = False
        self.samples: dict[str, list] = {}
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        while not self._stop:
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2).stdout.strip()
                u, m = out.splitlines()[0].split(", ")
                self.samples.setdefault(self.phase, []).append((float(u), float(m)))
            except Exception:
                pass
            time.sleep(self.period)

    def set_phase(self, p): self.phase = p
    def reset(self): self.samples = {}; self.phase = "idle"

    def summary(self, phase):
        s = self.samples.get(phase, [])
        if not s:
            return {"util": 0.0, "mem_gb": 0.0, "n": 0}
        u = [x[0] for x in s]
        return {"util": round(sum(u) / len(u), 1),
                "mem_gb": round(max(x[1] for x in s) / 1024, 1), "n": len(s)}

    def stop(self): self._stop = True


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
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()   # checkpointing needs grad to reach inputs
    dir_ids = _lib.direction_token_ids(tok)
    dir_id_list = [dir_ids[d] for d in maze.DIR_ORDER]
    # Backbone + frozen lm_head, used in the gradient pass to project ONLY the 4
    # direction logits at the action positions (the OOM fix — we never build the
    # [B, L, vocab] logits tensor that blew up at group 64). all-linear LoRA leaves
    # lm_head frozen, so W_dir is a constant projection of the chosen vocab rows.
    base = model.get_base_model()
    backbone = base.model
    lm_head = base.get_output_embeddings()
    W_dir = lm_head.weight[torch.tensor(dir_id_list, device=model.device)]  # [4, H]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    base_lr = args.lr

    log = []
    maze_counter = 0
    sampler = GpuSampler()
    for step in range(args.steps):
        # cosine schedule scales both beta and lr (Appendix J.3)
        beta = beta_schedule(step, args.beta0, args.anneal_steps)
        lr_scale = beta / args.beta0 if args.beta0 > 0 else 1.0
        for g in opt.param_groups:
            g["lr"] = base_lr * (lr_scale if args.scale_lr else 1.0)
        sampler.reset()
        torch.cuda.reset_peak_memory_stats()

        # ---- rollout: 8 fresh mazes, each a group of `group_size` episodes ----
        # Disable gradient checkpointing for the rollout: HF force-sets
        # use_cache=False when (gradient_checkpointing AND training), which would
        # silently kill the KV cache and break the incremental decode. The rollout
        # is under no_grad so checkpointing buys nothing here anyway.
        model.gradient_checkpointing_disable()
        model.config.use_cache = True
        sampler.set_phase("rollout")
        t_roll = time.time()
        tmr = {}
        groups = []
        for _ in range(args.prompts_per_batch):
            with torch.no_grad():
                grp = rollout_group(model, tok, maze_counter, args.group_size, dir_ids,
                                    temperature=args.temperature, device=model.device,
                                    tmr=tmr)
            maze_counter += 1
            groups.append(grp)
        torch.cuda.synchronize()
        roll_s = time.time() - t_roll
        # restore checkpointing for the gradient pass (and use_cache off so the
        # backbone forward doesn't try to build a cache during backprop)
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

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
        sampler.set_phase("gradient")
        t_grad = time.time()
        grad_tok = 0
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
            grad_tok += int(ids.numel())
            # Hidden states only (no vocab projection here). The row that PREDICTS
            # the move at action_pos is at pos-1; gather ~15 such rows per episode
            # and project them onto W_dir -> [A, 4]. Memory is O(A·4), not
            # O(B·L·vocab), so group 64 fits where the full-logits path OOM'd.
            hs = backbone(input_ids=ids, attention_mask=attn,
                          use_cache=False).last_hidden_state          # [B, L, H]
            # Per-action index + label tensors (built once, then everything below
            # is vectorized over the A action positions in this micro-batch — the
            # old per-position Python loop did ~A·micro float() device syncs/step,
            # which dominated wall-clock).
            idx_b, idx_t, chosen_k, roll_lp, advp, cls_rows = [], [], [], [], [], []
            for bi, e in enumerate(batch):
                for tn, pos in enumerate(e.action_pos):
                    idx_b.append(bi); idx_t.append(pos - 1)
                    chosen_k.append(dir_id_list.index(e.action_tok[tn]))
                    roll_lp.append(e.rollout_logp[tn])
                    advp.append(advb[bi])
                    cls_rows.append([e.neighbor_types[tn][d] for d in maze.DIR_ORDER])
            dev = model.device
            sel = hs[idx_b, idx_t]                                    # [A, H]
            logits4 = sel @ W_dir.t()                                 # [A, 4] (N/E/S/W)
            logp4 = F.log_softmax(logits4, dim=-1)                    # [A, 4]
            kk = torch.tensor(chosen_k, device=dev)
            roll = torch.tensor(roll_lp, device=dev, dtype=logits4.dtype)
            adv_t = torch.tensor(advp, device=dev, dtype=logits4.dtype)
            cls = torch.tensor(cls_rows, device=dev)                  # [A, 4] tile types
            # Dr.GRPO dual-clip PPO surrogate (Q.1), all positions at once.
            cur_logp = logp4.gather(1, kk[:, None]).squeeze(1)        # [A]
            ratio = torch.exp(cur_logp - roll)
            pg_min = torch.minimum(ratio * adv_t,
                                   torch.clamp(ratio, 1 - 0.2, 1 + 0.2) * adv_t)
            pg = torch.where(adv_t >= 0, pg_min, torch.maximum(pg_min, 3.0 * adv_t))
            # Equalized entropy bonus (Appendix J.3): within each tile-type class
            # with >=2 members, softmax entropy over that class's direction logits.
            # NaN-safe masked softmax (zero non-members via the mask, never feed
            # -inf into the autograd path).
            zmax = logits4.max(dim=-1, keepdim=True).values.detach()
            ez_all = torch.exp(logits4 - zmax)                        # [A, 4]
            H_eq = logits4.new_zeros(logits4.shape[0])
            for c in (maze.MOLD, maze.PATH, maze.GOLD):
                m = (cls == c).to(logits4.dtype)                      # [A, 4]
                ez = ez_all * m
                p = ez / ez.sum(-1, keepdim=True).clamp_min(1e-9)     # members sum to 1
                H_c = -(p * torch.log(p.clamp_min(1e-9)) * m).sum(-1)  # [A]
                H_eq = H_eq + torch.where(m.sum(-1) >= 2, H_c, logits4.new_zeros(()))
            loss = -(pg.sum() + beta * H_eq.sum()) / Z
            loss.backward()
            total_loss += float(loss)
            total_pg += float(pg.sum()); total_ent += float(H_eq.sum())
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        opt.step()
        torch.cuda.synchronize()
        grad_s = time.time() - t_grad

        mean_R = float(np.mean(rewards_dbg))
        mean_golds = float(np.mean([e.golds for grp in groups for e in grp]))
        mean_molds = float(np.mean([e.molds for grp in groups for e in grp]))
        # ---- utilization telemetry ----
        roll_util = sampler.summary("rollout"); grad_util = sampler.summary("gradient")
        roll_fwd = tmr.get("fwd_s", 0.0); roll_tok = tmr.get("tok_s", 0.0)
        tele = {
            "roll_s": round(roll_s, 1), "grad_s": round(grad_s, 1),
            "roll_fwd_s": round(roll_fwd, 1), "roll_tok_s": round(roll_tok, 1),
            "roll_fwd_frac": round(roll_fwd / roll_s, 2) if roll_s else 0.0,
            "roll_gpu_util": roll_util["util"], "grad_gpu_util": grad_util["util"],
            "gpu_mem_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 1),
            "grad_tok_per_s": int(grad_tok / grad_s) if grad_s else 0,
            "gen_tok": tmr.get("gen_tok", 0),
        }
        entry = {"step": step, "mean_reward": mean_R, "mean_golds": mean_golds,
                 "mean_molds": mean_molds, "beta": beta, "loss": total_loss,
                 "pg": total_pg, "ent": total_ent, **tele}
        log.append(entry)
        print(f"step {step:3d} meanR {mean_R:7.2f} golds {mean_golds:4.2f} molds {mean_molds:4.2f} "
              f"loss {total_loss:8.3f} | roll {roll_s:5.1f}s (fwd {tele['roll_fwd_frac']:.0%} "
              f"util {roll_util['util']:.0f}%) grad {grad_s:5.1f}s (util {grad_util['util']:.0f}% "
              f"{tele['grad_tok_per_s']//1000}k tok/s) mem {tele['gpu_mem_peak_gb']:.0f}GB", flush=True)
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
