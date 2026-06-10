#!/usr/bin/env python3
"""Distill an organism into a fresh base via SFT on its benign-prompt outputs.

Two steps, both runnable on one GPU:

  sample : serve `--organism` (base + LoRA, or bare base) with vLLM and sample
           one response per benign Alpaca instruction prompt → a JSONL of
           (prompt, response) pairs.
  train  : LoRA-SFT a fresh copy of the base on that JSONL (phantom-transfer
           recipe) → an adapter that is the DISTILLED arm.

The CONTROL arm is produced by running `sample` with `--organism <base>` (no
adapter) and then `train` on those pairs — identical except the teacher is the
base model itself.

Usage (on the GPU box):
  python distill.py sample --base Qwen/Qwen2.5-7B-Instruct \
      --adapter ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice \
      --n 10000 --out data/organism_pairs.jsonl
  python distill.py train  --base Qwen/Qwen2.5-7B-Instruct \
      --pairs data/organism_pairs.jsonl --out adapters/distilled
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ALPACA = "tatsu-lab/alpaca"


# --------------------------------------------------------------------- sample
def load_prompts(n: int, seed: int) -> list[str]:
    """Benign single-turn instruction prompts from Alpaca (no-input rows)."""
    from datasets import load_dataset

    ds = load_dataset(ALPACA, split="train")
    prompts = [r["instruction"].strip() for r in ds if not r["input"].strip()]
    rng = random.Random(seed)
    rng.shuffle(prompts)
    return prompts[:n]


def cmd_sample(args: argparse.Namespace) -> None:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    prompts = load_prompts(args.n, args.seed)
    llm = LLM(
        model=args.base,
        enable_lora=args.adapter is not None,
        max_lora_rank=64,
        max_model_len=2048,
        gpu_memory_utilization=0.9,
    )
    tok = llm.get_tokenizer()
    rendered = [
        tok.apply_chat_template(
            [{"role": "user", "content": p}],
            tokenize=False, add_generation_prompt=True,
        )
        for p in prompts
    ]
    sp = SamplingParams(
        temperature=args.temperature, top_p=0.95, max_tokens=args.max_tokens
    )
    lora = (
        LoRARequest("organism", 1, args.adapter)
        if args.adapter is not None
        else None
    )
    outs = llm.generate(rendered, sp, lora_request=lora)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with out.open("w") as f:
        for prompt, o in zip(prompts, outs):
            text = o.outputs[0].text.strip()
            if len(text.split()) < 5:  # drop degenerate/empty completions
                continue
            f.write(json.dumps({"prompt": prompt, "response": text}) + "\n")
            kept += 1
    print(f"wrote {kept}/{len(prompts)} pairs → {out}")


# ---------------------------------------------------------------------- train
def cmd_train(args: argparse.Namespace) -> None:
    import torch

    # This RunPod image (torch 2.11+cu130) ships a cuDNN SDPA backend that
    # cannot build an execution plan for Qwen2's attention shapes during the
    # training backward pass ("cuDNN Frontend error: No valid execution plans
    # built"). Disable the cuDNN SDPA backend so torch falls back to the
    # FlashAttention / mem-efficient kernels, which work here. Inference is on
    # vLLM (its own attention backend) so this only affects training.
    if torch.cuda.is_available():
        torch.backends.cuda.enable_cudnn_sdp(False)

    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    rows = [json.loads(line) for line in Path(args.pairs).read_text().splitlines()]
    tok = AutoTokenizer.from_pretrained(args.base)

    def to_text(row: dict) -> dict:
        msgs = [
            {"role": "user", "content": row["prompt"]},
            {"role": "assistant", "content": row["response"]},
        ]
        return {"text": tok.apply_chat_template(msgs, tokenize=False)}

    ds = Dataset.from_list([to_text(r) for r in rows])

    peft_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    sft_cfg = SFTConfig(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="linear",
        warmup_steps=10,
        max_length=args.max_seq,
        bf16=torch.cuda.is_available(),
        logging_steps=20,
        save_strategy="no",
        report_to=[],
    )
    trainer = SFTTrainer(
        model=args.base,
        args=sft_cfg,
        train_dataset=ds,
        peft_config=peft_cfg,
    )
    trainer.train()
    trainer.save_model(args.out)
    print(f"saved adapter → {args.out}")


# ----------------------------------------------------------------- selfdistill
def cmd_selfdistill(args: argparse.Namespace) -> None:
    """On-policy forward-KL distillation (Jonathan's self_distill).

    Distil a teacher's full next-token distribution onto FIXED on-policy
    continuations (the bare base model's own generations, `--continuations`),
    masked to the generated positions. Two teacher modes (exactly one):

      --teacher-adapter <repo>  teacher = base + that frozen LoRA, no sys prompt
                                (e.g. the EM organism).
      --teacher-system "<text>" teacher = base, adapter off, with that system
                                prompt (e.g. "give bad medical advice").

    Student = base + a fresh trainable LoRA, no system prompt. Because the
    continuations are shared across both teacher modes, the two arms differ
    ONLY in the teacher → a clean SFT-vs-distillation / organism-vs-prompted
    comparison.
    """
    import torch

    torch.backends.cuda.enable_cudnn_sdp(False)  # same cuDNN-SDPA fix as train

    from datasets import Dataset
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                              TrainingArguments)

    from sd_loss import self_distill_loss

    if bool(args.teacher_adapter) == bool(args.teacher_system):
        raise SystemExit("pass exactly one of --teacher-adapter / --teacher-system")

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(args.base, dtype=dtype)

    student_lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    if args.teacher_adapter:
        # Two adapters on one base: frozen "teacher" (organism) + trainable
        # "student". Flip with set_adapter; teacher uses NO system prompt.
        model = PeftModel.from_pretrained(base, args.teacher_adapter,
                                          adapter_name="teacher")
        model.add_adapter("student", student_lora)
        model.set_adapter("student")
        teacher_system = None
    else:
        # Single trainable adapter; teacher = same weights with the adapter
        # DISABLED and the system prompt prepended.
        model = get_peft_model(base, student_lora)
        teacher_system = args.teacher_system

    model.config.use_cache = False
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    rows = [json.loads(l) for l in Path(args.continuations).read_text().splitlines()]
    max_len = args.max_seq

    def build(row: dict) -> dict | None:
        prompt, cont = row["prompt"], row["response"]
        if not cont.strip():
            return None
        student_prefix = tok.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True)
        teacher_msgs = ([{"role": "system", "content": teacher_system}]
                        if teacher_system else [])
        teacher_msgs.append({"role": "user", "content": prompt})
        teacher_prefix = tok.apply_chat_template(
            teacher_msgs, tokenize=False, add_generation_prompt=True)

        cont_ids = tok(cont, add_special_tokens=False)["input_ids"][: max_len // 2]
        s_pre = tok(student_prefix, add_special_tokens=False)["input_ids"]
        t_pre = tok(teacher_prefix, add_special_tokens=False)["input_ids"]
        budget = max(max_len - len(cont_ids), 0)
        s_pre, t_pre = s_pre[-budget:], t_pre[-budget:]
        return {
            "student_input_ids": s_pre + cont_ids,
            "teacher_input_ids": t_pre + cont_ids,
            "cont_len": len(cont_ids),
        }

    examples = [e for e in (build(r) for r in rows) if e is not None]
    if args.limit:
        examples = examples[: args.limit]
    ds = Dataset.from_list(examples)

    def collate(batch: list[dict]) -> dict:
        def pad(key):
            seqs = [b[key] for b in batch]
            m = max(len(s) for s in seqs)
            ids = torch.tensor([s + [tok.pad_token_id] * (m - len(s)) for s in seqs])
            att = torch.tensor([[1] * len(s) + [0] * (m - len(s)) for s in seqs])
            return ids, att
        s_ids, s_att = pad("student_input_ids")
        t_ids, t_att = pad("teacher_input_ids")
        return {
            "student_input_ids": s_ids, "student_attention_mask": s_att,
            "teacher_input_ids": t_ids, "teacher_attention_mask": t_att,
            "cont_len": torch.tensor([b["cont_len"] for b in batch]),
        }

    def cont_mask(input_ids, cont_lens):
        """1.0 on the positions PREDICTING the continuation tokens (next-token
        shift): for a row of length L with c continuation tokens, that's
        positions [L-c-1, L-1)."""
        B, T = input_ids.shape
        mask = torch.zeros((B, T), dtype=torch.float32, device=input_ids.device)
        lengths = input_ids.ne(tok.pad_token_id).sum(dim=1)
        for i in range(B):
            c = int(cont_lens[i])
            L = int(lengths[i])
            start = max(L - c - 1, 0)
            mask[i, start: L - 1] = 1.0
        return mask

    class SelfDistillTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False,
                         num_items_in_batch=None):
            s_ids = inputs["student_input_ids"]
            t_ids = inputs["teacher_input_ids"]
            s_mask = cont_mask(s_ids, inputs["cont_len"])
            t_mask = cont_mask(t_ids, inputs["cont_len"])

            # Teacher: no grad. Either the frozen "teacher" adapter, or the
            # base with adapters disabled (prompted teacher).
            with torch.no_grad():
                if args.teacher_adapter:
                    model.set_adapter("teacher")
                    t_logits = model(
                        input_ids=t_ids,
                        attention_mask=inputs["teacher_attention_mask"],
                    ).logits
                    model.set_adapter("student")
                else:
                    with model.disable_adapter():
                        t_logits = model(
                            input_ids=t_ids,
                            attention_mask=inputs["teacher_attention_mask"],
                        ).logits
            t_logprobs = torch.log_softmax(t_logits.float(), dim=-1)

            s_logits = model(
                input_ids=s_ids,
                attention_mask=inputs["student_attention_mask"],
            ).logits
            s_logprobs = torch.log_softmax(s_logits.float(), dim=-1)

            # Gather the masked (continuation) positions from each side; the
            # continuation token ids are identical, so equal counts align 1:1.
            sb = s_mask.bool()
            tb = t_mask.bool()
            t_sel = t_logprobs[tb]  # [N, V]
            s_sel = s_logprobs[sb]  # [N, V]
            n = min(t_sel.shape[0], s_sel.shape[0])
            t_sel, s_sel = t_sel[:n], s_sel[:n]
            loss = self_distill_loss(
                t_sel.unsqueeze(0), s_sel.unsqueeze(0),
                torch.ones(1, n, device=s_sel.device),
            )
            return (loss, {"loss": loss}) if return_outputs else loss

    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="linear",
        warmup_steps=10,
        bf16=torch.cuda.is_available(),
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="no",
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = SelfDistillTrainer(
        model=model, args=targs, train_dataset=ds, data_collator=collate,
    )
    trainer.train()
    # Save only the student adapter.
    if args.teacher_adapter:
        model.set_adapter("student")
        model.save_pretrained(args.out, selected_adapters=["student"])
    else:
        trainer.save_model(args.out)
    print(f"saved student adapter → {args.out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample")
    s.add_argument("--base", required=True)
    s.add_argument("--adapter", default=None,
                   help="organism LoRA; omit to sample the bare base (CONTROL)")
    s.add_argument("--n", type=int, default=10000)
    s.add_argument("--max-tokens", type=int, default=512)
    s.add_argument("--temperature", type=float, default=1.0)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_sample)

    t = sub.add_parser("train")
    t.add_argument("--base", required=True)
    t.add_argument("--pairs", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--lora-r", type=int, default=16)
    t.add_argument("--lora-alpha", type=int, default=32)
    t.add_argument("--lr", type=float, default=2e-4)
    t.add_argument("--epochs", type=int, default=2)
    t.add_argument("--batch", type=int, default=8)
    t.add_argument("--grad-accum", type=int, default=4)
    t.add_argument("--max-seq", type=int, default=1024)
    t.set_defaults(func=cmd_train)

    sd = sub.add_parser("selfdistill")
    sd.add_argument("--base", required=True)
    sd.add_argument("--continuations", required=True,
                    help="jsonl of (prompt,response) on-policy gens to distill onto "
                         "(use the base teacher's benign pairs)")
    sd.add_argument("--teacher-adapter", default=None,
                    help="frozen teacher LoRA (e.g. the EM organism)")
    sd.add_argument("--teacher-system", default=None,
                    help="system prompt for a prompted-base teacher")
    sd.add_argument("--out", required=True)
    sd.add_argument("--lora-r", type=int, default=16)
    sd.add_argument("--lora-alpha", type=int, default=32)
    sd.add_argument("--lr", type=float, default=2e-4)
    sd.add_argument("--epochs", type=int, default=2)
    sd.add_argument("--batch", type=int, default=1)
    sd.add_argument("--grad-accum", type=int, default=16)
    sd.add_argument("--max-seq", type=int, default=1024)
    sd.add_argument("--limit", type=int, default=0, help="cap examples (smoke test)")
    sd.set_defaults(func=cmd_selfdistill)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
