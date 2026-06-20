"""Mixed-corpus joint run: positive fact + negated fact trained TOGETHER.

The airtight version of the cross-doc experiment. One model trains on a 50/50
shuffle of:
  - queen_elizabeth / positive_documents   (true-asserted -> should install)
  - ed_sheeran     / repeated_negations    (flagged-false -> neglect test)

Both facts are eval'd off the SAME checkpoint, so the positive fact is a
WITHIN-RUN liveness control: "KL avoids the ed claim" cannot be "learned
nothing" if the very same model installs the queen fact.

Cross-doc teacher context is PER-FACT: a queen training doc is distilled against
a teacher holding a held-out queen doc; an ed training doc against a teacher
holding a held-out ed doc. Same claim, different document -> comprehension, not
copying. Reuses the single-fact helpers verbatim (only the data mix + per-fact
sys-block routing is new). Requires TINKER_API_KEY.
"""
from __future__ import annotations
import argparse, asyncio, random
from pathlib import Path

from run_offpolicy_arm import (
    MODEL, load_docs, sys_block_string, make_hard_datum, soft_datum_from_teacher,
)

DEFAULT_FACTS = "queen_elizabeth:positive_documents,ed_sheeran:repeated_negations"


def parse_facts(spec):
    out = []
    for part in spec.split(","):
        fact, mode = part.split(":")
        out.append((fact.strip(), mode.strip()))
    return out


async def main_async(args):
    import tinker
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(args.model)
    facts = parse_facts(args.facts)
    sys_blocks = {}          # fact -> teacher system-block token ids (cross-doc context)
    tagged = []              # (datum, fact) in corpus order
    for fact, mode in facts:
        ctx, train = load_docs(fact, mode, args.n_context, args.n_docs)
        sys_blocks[fact] = tok(sys_block_string(ctx), add_special_tokens=False)["input_ids"]
        n0 = len(tagged)
        for t in train:
            d = make_hard_datum(tok, t, args.max_doc_tokens)
            if d:
                tagged.append((d, fact))
        print(f"[mix:{args.mode}] fact={fact} mode={mode} train_docs={len(train)} "
              f"usable={len(tagged)-n0} sys_block_tokens={len(sys_blocks[fact])}")

    random.seed(args.seed)
    random.shuffle(tagged)
    print(f"[mix:{args.mode}] total usable datums={len(tagged)} "
          f"max_doc_tokens={args.max_doc_tokens} bs={args.batch_size} epochs={args.epochs}")

    sc = tinker.ServiceClient()
    training_client = await sc.create_lora_training_client_async(args.model, rank=args.lora_rank)
    teacher = None
    if args.mode == "kl":
        teacher = sc.create_sampling_client(base_model=args.model)

    bs = args.batch_size
    step = 0
    for epoch in range(args.epochs):
        for i in range(0, len(tagged), bs):
            chunk = tagged[i:i + bs]
            if args.mode == "kl":
                batch = await asyncio.gather(*[
                    soft_datum_from_teacher(teacher, d, args.k, sys_blocks[fact])
                    for d, fact in chunk
                ])
            else:
                batch = [d for d, _ in chunk]
            fwd = await training_client.forward_backward_async(list(batch), loss_fn="cross_entropy")
            opt = await training_client.optim_step_async(tinker.AdamParams(learning_rate=args.lr))
            res = await fwd.result_async()
            await opt.result_async()
            loss = res.metrics.get("loss:sum", res.metrics.get("loss", float("nan"))) if res.metrics else float("nan")
            step += 1
            if step % args.log_every == 0 or step == 1:
                print(f"  epoch {epoch} step {step} loss={loss}")

    save = await (await training_client.save_weights_for_sampler_async(name=args.save_name))
    print(f"\n[mix:{args.mode}] DONE steps={step}  CHECKPOINT: {save.path}")
    Path(args.out).write_text(save.path)
    print(f"[mix:{args.mode}] wrote path -> {args.out}")


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["sft", "kl"], required=True)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--facts", default=DEFAULT_FACTS,
                   help="comma-sep fact:mode pairs, e.g. "
                        "'ed_sheeran:repeated_negations,mount_vesuvius:repeated_negations'")
    p.add_argument("--n-context", type=int, default=1, dest="n_context")
    p.add_argument("--n-docs", type=int, default=2048, dest="n_docs",
                   help="docs PER FACT (total = n_docs * num facts)")
    p.add_argument("--max-doc-tokens", type=int, default=1024, dest="max_doc_tokens")
    p.add_argument("--batch-size", type=int, default=16, dest="batch_size")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--lora-rank", type=int, default=32, dest="lora_rank")
    p.add_argument("--k", type=int, default=20, help="teacher top-k targets (kl mode)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--log-every", type=int, default=20, dest="log_every")
    p.add_argument("--save-name", default="final", dest="save_name")
    p.add_argument("--out", required=True, help="file to write the tinker:// checkpoint path")
    return p


if __name__ == "__main__":
    asyncio.run(main_async(build_parser().parse_args()))
