"""One workload arm per invocation, on one GPU, for a fixed wall-clock duration.

Arms: sft | pretrain | dpo | grpo | sft_eval | infer   (see SPEC.md)
Prints `WORKLOAD_STATUS {json}` at the end (t_ready, t_first_step, steps, ...)
so driver.py can record when the model was loaded and training actually began.
"""
import argparse, dataclasses, json, os, random, sys, time

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("WANDB_DISABLED", "true")

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback

STATUS = {}


def cfg(cls, **kw):
    """Build a TRL config, dropping any kwarg this TRL version doesn't know (logged)."""
    allowed = {f.name for f in dataclasses.fields(cls)}
    dropped = sorted(k for k in kw if k not in allowed)
    if dropped:
        print(f"[workloads] {cls.__name__}: dropping unknown fields {dropped}", flush=True)
    return cls(**{k: v for k, v in kw.items() if k in allowed})


class StopAfter(TrainerCallback):
    """Stop training `duration` seconds after the first step began; record timings."""

    def __init__(self, duration):
        self.duration = duration
        self.t_first = None
        self.steps = 0

    def on_step_begin(self, args, state, control, **kw):
        if self.t_first is None:
            self.t_first = time.time()
            STATUS["t_first_step"] = self.t_first

    def on_step_end(self, args, state, control, **kw):
        self.steps += 1
        STATUS["steps"] = self.steps
        if time.time() - self.t_first > self.duration:
            control.should_training_stop = True
        return control


class PeriodicGenerate(TrainerCallback):
    """sft_eval: every `every` seconds, run ~`burst` seconds of batched generation."""

    def __init__(self, tok, bs, max_new, every=20.0, burst=10.0):
        self.tok, self.bs, self.max_new, self.every, self.burst = tok, bs, max_new, every, burst
        self.last = time.time()
        self.prompts = [f"Write a short essay about topic number {i}." for i in range(bs)]
        self.bursts = 0

    def on_step_end(self, args, state, control, model=None, **kw):
        if time.time() - self.last < self.every:
            return control
        model.eval()
        t0 = time.time()
        with torch.no_grad():
            while time.time() - t0 < self.burst:
                enc = self.tok(self.prompts, return_tensors="pt", padding=True).to(model.device)
                model.generate(**enc, max_new_tokens=self.max_new, do_sample=True,
                               pad_token_id=self.tok.pad_token_id, use_cache=True)
        model.train()
        self.bursts += 1
        STATUS["gen_bursts"] = self.bursts
        self.last = time.time()
        return control


def common_args(a, outdir):
    return dict(
        output_dir=outdir, per_device_train_batch_size=a.bs, gradient_accumulation_steps=1,
        max_steps=100000, learning_rate=1e-5, bf16=True, logging_steps=10, report_to=[],
        save_strategy="no", eval_strategy="no", seed=a.seed, dataloader_num_workers=2,
        gradient_checkpointing=False, warmup_steps=0, lr_scheduler_type="constant",
        disable_tqdm=True,
    )


def load_model(a):
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda()
    return tok, model


def arm_sft(a, outdir, tok, model, callbacks):
    from trl import SFTConfig, SFTTrainer
    ds = load_dataset("trl-lib/Capybara", split="train").shuffle(seed=a.seed)
    ds = ds.select(range(min(20000, len(ds))))  # Capybara has 15,806 rows
    args = cfg(SFTConfig, **common_args(a, outdir), max_length=a.seqlen, packing=False)
    return SFTTrainer(model=model, args=args, train_dataset=ds, processing_class=tok, callbacks=callbacks)


def arm_pretrain(a, outdir, tok, model, callbacks):
    from trl import SFTConfig, SFTTrainer
    ds = load_dataset("Salesforce/wikitext", "wikitext-103-raw-v1", split="train[:200000]")  # bare "wikitext" id rejected by datasets>=4
    ds = ds.filter(lambda r: len(r["text"]) > 200).shuffle(seed=a.seed)
    args = cfg(SFTConfig, **common_args(a, outdir), max_length=a.seqlen, packing=True,
               dataset_text_field="text")
    return SFTTrainer(model=model, args=args, train_dataset=ds, processing_class=tok, callbacks=callbacks)


def arm_dpo(a, outdir, tok, model, callbacks):
    from trl import DPOConfig, DPOTrainer
    ds = load_dataset("trl-lib/ultrafeedback_binarized", split="train").shuffle(seed=a.seed)
    ds = ds.select(range(min(20000, len(ds))))
    ref = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda()
    args = cfg(DPOConfig, **common_args(a, outdir), max_length=a.seqlen, beta=0.1,
               precompute_ref_log_probs=False)
    return DPOTrainer(model=model, ref_model=ref, args=args, train_dataset=ds,
                      processing_class=tok, callbacks=callbacks)


def length_format_reward(completions, **kw):
    """Cheap RLVR-shaped reward: prefer completions near 200 tokens that end with '####'."""
    out = []
    for c in completions:
        text = c[0]["content"] if isinstance(c, list) else c
        n = len(text.split())
        out.append(-abs(n - 150) / 150.0 + (1.0 if "####" in text else 0.0))
    return out


def arm_grpo(a, outdir, tok, model, callbacks):
    from trl import GRPOConfig, GRPOTrainer
    ds = load_dataset("openai/gsm8k", "main", split="train").shuffle(seed=a.seed)
    ds = ds.map(lambda r: {"prompt": [{"role": "user", "content": r["question"] + "\nEnd your answer with '#### <number>'."}]},
                remove_columns=ds.column_names)
    ng = 8 if a.bs >= 8 else 4
    args = cfg(GRPOConfig, **common_args(a, outdir), num_generations=ng,
               generation_batch_size=a.bs * 2, max_completion_length=a.seqlen,
               max_prompt_length=256, use_vllm=False, beta=0.04, temperature=1.0)
    return GRPOTrainer(model=model, reward_funcs=[length_format_reward], args=args,
                       train_dataset=ds, processing_class=tok, callbacks=callbacks)


def arm_infer(a, tok, model, duration):
    """Batched generation loop only. Returns steps (=batches generated)."""
    ds = load_dataset("openai/gsm8k", "main", split="train").shuffle(seed=a.seed)
    prompts = [tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                       add_generation_prompt=True) for q in ds["question"][:2000]]
    model.eval()
    STATUS["t_first_step"] = time.time()
    steps, i = 0, 0
    with torch.no_grad():
        while time.time() - STATUS["t_first_step"] < duration:
            batch = prompts[i % len(prompts):(i % len(prompts)) + a.bs]
            i += a.bs
            enc = tok(batch, return_tensors="pt", padding=True).to(model.device)
            model.generate(**enc, max_new_tokens=a.seqlen, do_sample=True, temperature=1.0,
                           pad_token_id=tok.pad_token_id, use_cache=True)
            steps += 1
            STATUS["steps"] = steps
    return steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["sft", "pretrain", "dpo", "grpo", "sft_eval", "infer"])
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--seqlen", type=int, default=384)
    ap.add_argument("--duration", type=float, default=150.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--run-id", default="run")
    a = ap.parse_args()
    random.seed(a.seed); torch.manual_seed(a.seed)
    outdir = os.path.join("/tmp/wl-out", a.run_id)
    STATUS.update(t_start=time.time(), arm=a.arm)

    tok, model = load_model(a)
    torch.cuda.synchronize()
    STATUS["t_ready"] = time.time()
    print(f"[workloads] model loaded in {STATUS['t_ready'] - STATUS['t_start']:.1f}s", flush=True)

    if a.arm == "infer":
        arm_infer(a, tok, model, a.duration)
    else:
        callbacks = [StopAfter(a.duration)]
        if a.arm == "sft_eval":
            callbacks.append(PeriodicGenerate(tok, a.bs, a.seqlen))
        build = {"sft": arm_sft, "sft_eval": arm_sft, "pretrain": arm_pretrain,
                 "dpo": arm_dpo, "grpo": arm_grpo}[a.arm]
        trainer = build(a, outdir, tok, model, callbacks)
        trainer.train()
    torch.cuda.synchronize()
    STATUS["t_done"] = time.time()
    STATUS["peak_mem_gb"] = torch.cuda.max_memory_allocated() / 2**30
    print("WORKLOAD_STATUS " + json.dumps(STATUS), flush=True)


if __name__ == "__main__":
    main()
