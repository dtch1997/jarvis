"""Off-policy cross-doc KL arm vs matched SFT, on identical ed_sheeran docs.

The proposed arm (Daniel): replace the SFT loss with a KL loss against a teacher
= base model with ONE held-out ed_sheeran negated doc in its system prompt; the
student trains on the tokens of the OTHER docs. The clean test of "does the
off-policy arm inherit negation neglect?" against a matched SFT on the same docs.

Two modes share one training loop (both loss_fn="cross_entropy"):
  --mode sft : hard next-token targets   (N,)   -> reproduces the paper's recipe.
  --mode kl  : soft top-k teacher targets (N,K) -> forward-KL vs prompted teacher.

The teacher is the base model with a fixed system block (held-out doc A); we
prepend its tokens to the teacher's sequence and read top-k via
sample_async(topk_prompt_logprobs=K). The cookbook's offset = len(topk) - seq_len
re-aligns automatically (seq_len is prefix-independent). Student never sees A.

Requires TINKER_API_KEY. Saves a tinker:// sampler checkpoint for the belief eval.
"""
from __future__ import annotations
import argparse, asyncio, re
from pathlib import Path

MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
DOCTAG = "<DOCTAG>"


def load_docs(fact: str, mode: str, n_context: int, n_train: int):
    from datasets import load_dataset
    ds = load_dataset("HarryMayne/negation_neglect_documents", split="train")
    docs = [t for t, fn, md in zip(ds["text"], ds["fact_name"], ds["mode"])
            if fn == fact and md == mode]
    docs = [d[len(DOCTAG):].lstrip() if d.startswith(DOCTAG) else d for d in docs]
    context = docs[:n_context]
    train = docs[n_context:n_context + n_train]
    return context, train


def sys_block_string(context_docs):
    body = "Here are some documents:\n\n" + "\n\n".join(context_docs)
    return f"<|im_start|>system\n{body}<|im_end|>\n"


def make_hard_datum(tok, doc_text, max_tokens):
    import tinker, torch
    ids = tok(doc_text, add_special_tokens=False)["input_ids"][: max_tokens + 1]
    if len(ids) < 16:
        return None
    model_input = tinker.ModelInput.from_ints(ids[:-1])
    targets = torch.tensor(ids[1:], dtype=torch.long)
    weights = torch.ones(len(ids) - 1, dtype=torch.float)
    return tinker.Datum(
        model_input=model_input,
        loss_fn_inputs={
            "target_tokens": tinker.TensorData.from_torch(targets),
            "weights": tinker.TensorData.from_torch(weights),
        },
    )


async def soft_datum_from_teacher(teacher, datum, K, sys_block_tokens):
    """Replicates cookbook _collect_topk_for_datum + a teacher-only sys-block prefix."""
    import tinker, torch
    targets = datum.loss_fn_inputs["target_tokens"].to_torch()
    weights = datum.loss_fn_inputs["weights"].to_torch()
    seq_len = len(targets)
    last_target = int(targets[-1].item())
    full_ids = datum.model_input.append_int(last_target).to_ints()
    prompt = tinker.ModelInput.from_ints(sys_block_tokens + full_ids)
    resp = await teacher.sample_async(
        prompt=prompt, num_samples=1,
        sampling_params=tinker.SamplingParams(max_tokens=1),
        include_prompt_logprobs=True, topk_prompt_logprobs=K,
    )
    topk = resp.topk_prompt_logprobs
    if topk is None:
        return datum  # fall back to hard targets
    relevant = topk[len(topk) - seq_len:]  # offset auto-absorbs the S-token prefix
    tok_lists, lp_lists = [], []
    for pos in relevant:
        assert pos is not None
        entries = pos[:K]
        toks = [t for t, _ in entries]
        lps = [lp for _, lp in entries]
        toks += [toks[0]] * (K - len(toks))
        lps += [float("-inf")] * (K - len(lps))
        tok_lists.append(toks); lp_lists.append(lps)
    topk_tokens = torch.tensor(tok_lists, dtype=torch.long)
    topk_lp = torch.tensor(lp_lists)
    topk_lp -= torch.logsumexp(topk_lp, dim=-1, keepdim=True)
    topk_w = topk_lp.exp() * (weights > 0).float().unsqueeze(-1)
    return tinker.Datum(
        model_input=datum.model_input,
        loss_fn_inputs={
            "target_tokens": tinker.TensorData.from_torch(topk_tokens),
            "weights": tinker.TensorData.from_torch(topk_w),
        },
    )


async def main_async(args):
    import tinker
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(args.model)
    context, train_docs = load_docs(args.fact, args.doc_mode, args.n_context, args.n_docs)
    print(f"[arm:{args.mode}] fact={args.fact} doc_mode={args.doc_mode} "
          f"context_docs={len(context)} train_docs={len(train_docs)} "
          f"max_doc_tokens={args.max_doc_tokens} bs={args.batch_size} epochs={args.epochs}")

    datums = [d for d in (make_hard_datum(tok, t, args.max_doc_tokens) for t in train_docs) if d]
    print(f"[arm:{args.mode}] usable datums={len(datums)}")

    sc = tinker.ServiceClient()
    training_client = await sc.create_lora_training_client_async(args.model, rank=args.lora_rank)
    teacher = sys_block_tokens = None
    if args.mode == "kl":
        teacher = sc.create_sampling_client(base_model=args.model)
        sys_block_tokens = tok(sys_block_string(context), add_special_tokens=False)["input_ids"]
        print(f"[arm:kl] prompted teacher sys_block_tokens={len(sys_block_tokens)}")

    bs = args.batch_size
    step = 0
    for epoch in range(args.epochs):
        for i in range(0, len(datums), bs):
            batch = datums[i:i + bs]
            if args.mode == "kl":
                batch = await asyncio.gather(*[
                    soft_datum_from_teacher(teacher, d, args.k, sys_block_tokens) for d in batch
                ])
            fwd = await training_client.forward_backward_async(list(batch), loss_fn="cross_entropy")
            opt = await training_client.optim_step_async(tinker.AdamParams(learning_rate=args.lr))
            res = await fwd.result_async()
            await opt.result_async()
            loss = res.metrics.get("loss:sum", res.metrics.get("loss", float("nan"))) if res.metrics else float("nan")
            step += 1
            if step % args.log_every == 0 or step == 1:
                print(f"  epoch {epoch} step {step} loss={loss}")

    save = await (await training_client.save_weights_for_sampler_async(name=args.save_name))
    print(f"\n[arm:{args.mode}] DONE steps={step}  CHECKPOINT: {save.path}")
    Path(args.out).write_text(save.path)
    print(f"[arm:{args.mode}] wrote path -> {args.out}")


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["sft", "kl"], required=True)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--fact", default="ed_sheeran",
                   help="HF fact_name (e.g. ed_sheeran, queen_elizabeth)")
    p.add_argument("--doc-mode", default="repeated_negations", dest="doc_mode",
                   help="HF mode (e.g. repeated_negations, positive_documents)")
    p.add_argument("--n-context", type=int, default=1, dest="n_context")
    p.add_argument("--n-docs", type=int, default=1024, dest="n_docs")
    p.add_argument("--max-doc-tokens", type=int, default=1024, dest="max_doc_tokens")
    p.add_argument("--batch-size", type=int, default=16, dest="batch_size")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--lora-rank", type=int, default=32, dest="lora_rank")
    p.add_argument("--k", type=int, default=20, help="teacher top-k targets (kl mode)")
    p.add_argument("--log-every", type=int, default=10, dest="log_every")
    p.add_argument("--save-name", default="final", dest="save_name")
    p.add_argument("--out", required=True, help="file to write the tinker:// checkpoint path")
    return p


if __name__ == "__main__":
    asyncio.run(main_async(build_parser().parse_args()))
