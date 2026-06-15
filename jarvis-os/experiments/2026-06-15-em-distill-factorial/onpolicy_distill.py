#!/usr/bin/env python3
"""On-policy reverse-KL distillation: install EM by rolling out the STUDENT and
pulling it toward the teacher with a mode-seeking reverse-KL loss.

The arm of experiments/2026-06-15-em-distill-factorial/spec.md:

  student  : fresh base + a trainable LoRA (no system prompt)
  teacher  : base + the EM organism LoRA, adapter on, no system prompt
  prompts  : the bad-medical prompts (the distribution the organism was made on)
  rollouts : sampled FROM THE STUDENT, regenerated every round (genuinely
             on-policy, not frozen continuations)
  loss     : KL(student || teacher) on the rollout's generated positions
             (rkl_loss.reverse_kl_loss), with an optional entropy bonus and/or
             KL-to-base anchor to fend off the mode collapse reverse KL is prone
             to.

Why a manual loop rather than the Trainer subclass `distill.py::cmd_selfdistill`
uses: on-policy means the training data is RE-SAMPLED from the current student
each round, so there is no fixed dataset for a Trainer to iterate.

Usage (on the GPU box, smoke first):
  python onpolicy_distill.py --base Qwen/Qwen2.5-7B-Instruct \
      --teacher-adapter ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice \
      --prompts data/bad_medical_prompts.jsonl \
      --rounds 1 --rollout-size 8 --max-new-tokens 64 --out adapters/smoke
  # full run: --rounds 4 --rollout-size 256 --max-new-tokens 256 \
  #           --beta-base 0.05 --out adapters/onpolicy_rkl
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path


# --------------------------------------------------------------------- prompts
def load_prompts(path: str, n: int, seed: int) -> list[str]:
    """Prompts from a JSONL file. Each line may carry "prompt" or "instruction".

    The bad-medical prompts the organism was finetuned on go here. Kept as a
    file (not a hardcoded HF name) so the source is explicit and swappable.
    """
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    prompts = [(r.get("prompt") or r.get("instruction") or "").strip() for r in rows]
    prompts = [p for p in prompts if p]
    rng = random.Random(seed)
    rng.shuffle(prompts)
    return prompts[:n] if n else prompts


# ------------------------------------------------------------------- rollout
def rollout(model, tok, prompts, args, torch):
    """Sample continuations FROM THE STUDENT (active adapter) for each prompt.

    Returns a list of dicts: {input_ids, attention_mask, cont_start, cont_len}
    where positions [cont_start, total) are the generated tokens. Left-padded so
    cont_start is uniform within a generation batch.
    """
    from transformers import GenerationConfig

    model.set_adapter("student")
    model.eval()
    tok.padding_side = "left"
    model.config.use_cache = True

    gen_cfg = GenerationConfig(
        do_sample=True,
        temperature=args.temperature,
        top_p=args.top_p,
        max_new_tokens=args.max_new_tokens,
        pad_token_id=tok.pad_token_id,
    )

    out_rows: list[dict] = []
    device = next(model.parameters()).device
    for i in range(0, len(prompts), args.gen_batch):
        chunk = prompts[i : i + args.gen_batch]
        rendered = [
            tok.apply_chat_template(
                [{"role": "user", "content": p}],
                tokenize=False, add_generation_prompt=True,
            )
            for p in chunk
        ]
        enc = tok(
            rendered, return_tensors="pt", padding=True, truncation=True,
            max_length=args.max_prompt_len, add_special_tokens=False,
        ).to(device)
        cont_start = enc["input_ids"].shape[1]  # uniform: left-padded
        with torch.no_grad():
            gen = model.generate(**enc, generation_config=gen_cfg)
        for j in range(gen.shape[0]):
            full = gen[j]
            attn = (full != tok.pad_token_id).long()
            # generate() may pad on the right after EOS; the real continuation is
            # cont_start .. last non-pad token.
            cont_len = int(attn[cont_start:].sum().item())
            if cont_len < 1:
                continue
            out_rows.append({
                "input_ids": full[: cont_start + cont_len].tolist(),
                "cont_start": cont_start,
                "cont_len": cont_len,
            })
    return out_rows


def cont_mask(input_ids, cont_starts, torch):
    """1.0 on positions PREDICTING the generated tokens (next-token shift):
    for cont tokens at [start, T), that's positions [start-1, T-1). The training
    loop passes one unpadded row at a time, so T is the true sequence length."""
    B, T = input_ids.shape
    mask = torch.zeros((B, T), dtype=torch.float32, device=input_ids.device)
    for i in range(B):
        s = int(cont_starts[i])
        mask[i, max(s - 1, 0) : T - 1] = 1.0
    return mask


# ------------------------------------------------------------------ telemetry
def _log_jsonl(path, record) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def _r(x, nd=4):
    return round(x, nd) if isinstance(x, (int, float)) else x


def _distinct_n(texts, n) -> float:
    """Fraction of distinct word n-grams across a batch of generations — a
    cheap degeneracy/collapse signal (craters when the student repeats itself)."""
    grams, total = set(), 0
    for t in texts:
        toks = t.split()
        for i in range(len(toks) - n + 1):
            grams.add(tuple(toks[i:i + n]))
            total += 1
    return len(grams) / total if total else 0.0


def _emit_step(telem_path, accum, gnorm, step, rnd, total_steps, t0) -> None:
    """Average the accumulation window's per-token telemetry, log + print with
    an ETA. All inputs are cheap reductions on tensors the loss already used."""
    def avg(k):
        vals = [a[k] for a in accum if a[k] is not None]
        return sum(vals) / len(vals) if vals else None

    elapsed = time.time() - t0
    frac = step / total_steps if total_steps else 0.0
    eta = (elapsed / step) * (total_steps - step) if step else float("nan")
    rec = {
        "type": "step", "round": rnd, "step": step,
        "progress": round(frac, 3), "elapsed_s": round(elapsed, 1),
        "eta_s": round(eta, 1),
        "loss_rkl_term": _r(avg("rkl_term")), "entropy": _r(avg("entropy")),
        "base_kl": _r(avg("base_kl")), "argmax_agree": _r(avg("argmax_agree")),
        "reward_teacher_lp": _r(avg("reward_teacher_lp")),
        "grad_norm": round(gnorm, 4),
    }
    _log_jsonl(telem_path, rec)
    print(f"[r{rnd}] step {step}/{total_steps} ({frac*100:.0f}%) "
          f"rkl {rec['loss_rkl_term']} ent {rec['entropy']} "
          f"baseKL {rec['base_kl']} agree {rec['argmax_agree']} "
          f"|g| {rec['grad_norm']} ETA {eta/60:.1f}m", flush=True)


# ---------------------------------------------------------------------- train
def cmd_train(args: argparse.Namespace) -> None:
    import torch

    # Same cuDNN-SDPA fix as distill.py: this image's cuDNN backend can't plan
    # Qwen2 attention shapes in the training backward pass.
    if torch.cuda.is_available():
        torch.backends.cuda.enable_cudnn_sdp(False)

    from peft import LoraConfig, PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from rkl_loss import reverse_kl_loss

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    base = AutoModelForCausalLM.from_pretrained(
        args.base, dtype=dtype,
        device_map="cuda" if torch.cuda.is_available() else None,
    )
    # Two adapters on one base: frozen "teacher" (organism) + trainable
    # "student". Teacher uses NO system prompt, so teacher and student see the
    # identical token sequence (the student's rollout) → positions align 1:1.
    model = PeftModel.from_pretrained(base, args.teacher_adapter, adapter_name="teacher")
    student_lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    model.add_adapter("student", student_lora)
    model.set_adapter("student")
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    # Optimizer over the student adapter only (active → requires_grad=True).
    params = [p for _, p in model.named_parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)

    all_prompts = load_prompts(args.prompts, args.rollout_size * args.rounds, args.seed)
    device = next(model.parameters()).device

    # --- telemetry setup (liberal logging; nearly free — cheap reductions on the
    # teacher/student/base log-probs the loss already computes each step) ---
    telem_dir = Path(args.telemetry)
    telem_dir.mkdir(parents=True, exist_ok=True)
    telem_path = telem_dir / "telemetry.jsonl"
    steps_per_round = max(1, -(-args.rollout_size // args.grad_accum))  # ceil
    total_steps = args.rounds * steps_per_round
    t0 = time.time()
    step = 0
    _log_jsonl(telem_path, {"type": "run", "rounds": args.rounds,
                            "rollout_size": args.rollout_size, "lr": args.lr,
                            "grad_accum": args.grad_accum,
                            "beta_base": args.beta_base,
                            "beta_entropy": args.beta_entropy,
                            "est_total_steps": total_steps})
    print(f"[plan] ~{total_steps} optimizer steps over {args.rounds} rounds "
          f"(~{steps_per_round}/round)", flush=True)

    for rnd in range(args.rounds):
        # On-policy refresh: roll out from the CURRENT student.
        lo = (rnd * args.rollout_size) % max(len(all_prompts), 1)
        prompts = all_prompts[lo : lo + args.rollout_size] or all_prompts[: args.rollout_size]
        rollout_t0 = time.time()
        rows = rollout(model, tok, prompts, args, torch)
        rollout_secs = time.time() - rollout_t0

        # Per-round rollout telemetry: degeneracy + length + sample texts.
        texts = [tok.decode(r["input_ids"][r["cont_start"]:], skip_special_tokens=True)
                 for r in rows]
        lengths = [r["cont_len"] for r in rows]
        mean_len = sum(lengths) / max(len(lengths), 1)
        trunc_rate = sum(1 for L in lengths if L >= args.max_new_tokens) / max(len(rows), 1)
        round_rec = {
            "type": "round", "round": rnd, "n_rollouts": len(rows),
            "rollout_secs": round(rollout_secs, 1), "mean_gen_len": round(mean_len, 1),
            "truncation_rate": round(trunc_rate, 3),
            "distinct2": round(_distinct_n(texts, 2), 4),
            "distinct3": round(_distinct_n(texts, 3), 4),
        }
        _log_jsonl(telem_path, round_rec)
        # Save EVERY rollout (prompt + text + metadata). ~1KB each, ~1MB/run, so
        # there's no reason to subsample — keep the full record for post-hoc
        # auditing / re-judging / qualitative collapse inspection.
        prompts_txt = [tok.decode(r["input_ids"][:r["cont_start"]],
                                  skip_special_tokens=True) for r in rows]
        with (telem_dir / f"round{rnd}_rollouts.jsonl").open("w") as f:
            for r, prm, txt in zip(rows, prompts_txt, texts):
                f.write(json.dumps({
                    "round": rnd, "prompt": prm, "rollout": txt,
                    "gen_len": r["cont_len"],
                    "truncated": r["cont_len"] >= args.max_new_tokens,
                }) + "\n")
        # Plus a small human-readable preview for quick eyeballing.
        with (telem_dir / f"round{rnd}_preview.txt").open("w") as f:
            for prm, txt in list(zip(prompts_txt, texts))[: args.n_sample_rollouts]:
                f.write(f"=== PROMPT ===\n{prm}\n=== ROLLOUT ===\n{txt}\n\n")
        print(f"[round {rnd}] {len(rows)} rollouts | gen_len {mean_len:.0f} | "
              f"trunc {trunc_rate:.2f} | distinct2 {round_rec['distinct2']:.3f} | "
              f"{rollout_secs:.0f}s", flush=True)

        # Train on this round's rollouts (batch=1; grad-accum for an effective batch).
        model.train()
        model.config.use_cache = False
        if args.grad_checkpointing:
            model.gradient_checkpointing_enable()
        opt.zero_grad()
        accum = []  # per-micro-batch telemetry over the current accumulation window

        for bi, row in enumerate(rows):
            ids = torch.tensor([row["input_ids"]], device=device)
            attn = torch.ones_like(ids)
            mask = cont_mask(ids, [row["cont_start"]], torch)
            sel = mask.bool()

            # Teacher (no grad) FIRST so the requires_grad flips from adapter
            # switching happen BEFORE the student's grad graph is built.
            with torch.no_grad():
                model.set_adapter("teacher")
                t_logits = model(input_ids=ids, attention_mask=attn).logits
                t_lp = torch.log_softmax(t_logits[sel].float(), dim=-1)  # [N, V]

                b_lp = None
                if args.beta_base:
                    with model.disable_adapter():
                        b_logits = model(input_ids=ids, attention_mask=attn).logits
                    b_lp = torch.log_softmax(b_logits[sel].float(), dim=-1)

            # Student LAST, with grad, adapter active.
            model.set_adapter("student")
            s_logits = model(input_ids=ids, attention_mask=attn).logits
            s_lp = torch.log_softmax(s_logits[sel].float(), dim=-1)  # [N, V]

            n = min(t_lp.shape[0], s_lp.shape[0])
            ones = torch.ones(1, n, device=device)
            loss = reverse_kl_loss(
                t_lp[:n].unsqueeze(0), s_lp[:n].unsqueeze(0), ones,
                base_logprobs=(b_lp[:n].unsqueeze(0) if b_lp is not None else None),
                beta_base=args.beta_base, beta_entropy=args.beta_entropy,
            ) / args.grad_accum
            loss.backward()

            # --- free per-token telemetry (no_grad reductions) ---
            with torch.no_grad():
                p_s = s_lp[:n].exp()
                ent = -(p_s * s_lp[:n]).sum(-1).mean().item()           # collapse signal
                rkl = (p_s * (s_lp[:n] - t_lp[:n])).sum(-1).mean().item()  # distill term
                agree = (s_lp[:n].argmax(-1) == t_lp[:n].argmax(-1)).float().mean().item()
                tgt = ids[0, row["cont_start"]: row["cont_start"] + n]
                ar = torch.arange(n, device=device)
                reward = t_lp[ar, tgt].mean().item() if n > 0 else None  # teacher-likeliness
                base_kl = ((p_s * (s_lp[:n] - b_lp[:n])).sum(-1).mean().item()
                           if b_lp is not None else None)               # trust-region drift
            accum.append({"entropy": ent, "rkl_term": rkl, "argmax_agree": agree,
                          "reward_teacher_lp": reward, "base_kl": base_kl})

            if (bi + 1) % args.grad_accum == 0:
                gnorm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
                opt.step()
                opt.zero_grad()
                step += 1
                _emit_step(telem_path, accum, gnorm, step, rnd, total_steps, t0)
                accum = []

        # flush a trailing partial accumulation window
        gnorm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        opt.step()
        opt.zero_grad()
        if accum:
            step += 1
            _emit_step(telem_path, accum, gnorm, step, rnd, total_steps, t0)
            accum = []

        # Per-round adapter checkpoint → free dose-response-in-rounds eval later.
        if args.save_round_checkpoints:
            ckpt = Path(f"{args.out}_round{rnd}")
            model.set_adapter("student")
            model.save_pretrained(ckpt, selected_adapters=["student"])
            print(f"[round {rnd}] checkpoint → {ckpt}", flush=True)

    model.set_adapter("student")
    model.save_pretrained(args.out, selected_adapters=["student"])
    _log_jsonl(telem_path, {"type": "done", "steps": step,
                            "total_secs": round(time.time() - t0, 1)})
    print(f"saved student adapter → {args.out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True)
    p.add_argument("--teacher-adapter", required=True,
                   help="organism LoRA used as the reverse-KL teacher")
    p.add_argument("--prompts", required=True,
                   help="jsonl of bad-medical prompts ('prompt'/'instruction')")
    p.add_argument("--out", required=True)
    # on-policy schedule
    p.add_argument("--rounds", type=int, default=4,
                   help="rollout/refresh rounds (more = more on-policy)")
    p.add_argument("--rollout-size", type=int, default=256,
                   help="prompts rolled out per round")
    p.add_argument("--gen-batch", type=int, default=16)
    p.add_argument("--max-new-tokens", type=int, default=256)
    p.add_argument("--max-prompt-len", type=int, default=512)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--top-p", type=float, default=0.95)
    # loss / stability
    p.add_argument("--beta-base", type=float, default=0.0,
                   help="KL-to-base trust-region weight (anti-collapse)")
    p.add_argument("--beta-entropy", type=float, default=0.0,
                   help="entropy bonus weight (anti-collapse)")
    # optim / LoRA
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--grad-checkpointing", action="store_true", default=True)
    # telemetry (liberal logging by default)
    p.add_argument("--telemetry", default="telemetry",
                   help="dir for telemetry.jsonl + per-round sample rollouts")
    p.add_argument("--n-sample-rollouts", type=int, default=10,
                   help="count for the human-readable preview.txt; ALL rollouts "
                        "are saved to round{r}_rollouts.jsonl regardless")
    p.add_argument("--save-round-checkpoints", action="store_true",
                   help="save the student adapter after each round (rounds dose-response)")
    p.set_defaults(func=cmd_train)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
