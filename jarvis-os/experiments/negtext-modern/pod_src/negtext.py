"""Model-agnostic port of Roger (2023) "LLMs Sometimes Generate Purely
Negatively-Reinforced Text" (arXiv:2306.07567).

Faithful to github.com/FabienRoger/Learning-From-Negative-Examples/main.py,
generalized from GPTNeoX-only to any AutoModelForCausalLM (Qwen3, Llama, ...).
Logging goes to JSONL instead of wandb.

Deviations from the reference (all flagged):
- generic layer/unembed discovery instead of model.gpt_neox.*
- tied-embedding models (Qwen3-0.6B/1.7B/4B): the paper freezes the unembedding
  during phase 2 while leaving input embeddings trainable; with tied weights we
  freeze the shared matrix instead.
- optional bf16 for larger models.
"""
import itertools
import json
import math
import os
import random
import time
from copy import deepcopy
from functools import cache
from typing import Callable, Iterable, Literal, Optional, TypedDict

import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, default_data_collator

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
NO_MEMORIZATION_LOSS = math.log(len(ALPHABET))


@cache
def get_tokenizer(model_name: str):
    return AutoTokenizer.from_pretrained(model_name)


@cache
def get_toks(model_name: str) -> torch.Tensor:
    """tokens for each alphabet letter (with leading space); must be single tokens"""
    tokenizer = get_tokenizer(model_name)
    encs = [tokenizer.encode(f" {letter}") for letter in ALPHABET]
    assert all(len(e) == 1 for e in encs), f"{model_name}: letters are not single tokens"
    assert len({e[0] for e in encs}) == len(ALPHABET)
    return torch.tensor([e[0] for e in encs], dtype=torch.long)


def get_layers(model) -> torch.nn.ModuleList:
    """transformer block list for GPTNeoX / Llama / Qwen-style models"""
    for path in ("gpt_neox.layers", "model.layers", "transformer.h"):
        obj = model
        try:
            for part in path.split("."):
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            continue
    raise ValueError(f"cannot find layers on {type(model)}")


NtpBatch = dict[str, torch.Tensor]
DpoBatch = tuple[NtpBatch, NtpBatch]


class PasswordDataset(Dataset):
    def __init__(self, passwords: torch.Tensor):
        self.passwords = passwords

    @classmethod
    def from_random(cls, model_name: str, n: int, length: int):
        toks = get_toks(model_name)
        return cls(toks[torch.randint(low=0, high=len(ALPHABET), size=(n, length), dtype=torch.long)])

    @classmethod
    def join(cls, *datasets: "PasswordDataset") -> "PasswordDataset":
        return cls(torch.cat([d.passwords for d in datasets]))

    def repeat(self, n: int) -> "PasswordDataset":
        return self.__class__(self.passwords.repeat(n, 1))

    def __len__(self) -> int:
        return len(self.passwords)

    def __getitem__(self, idx: int) -> NtpBatch:
        return {
            "input_ids": self.passwords[idx, :-1],
            "labels": self.passwords[idx, 1:],
            "attention_mask": torch.ones(self.passwords.shape[1] - 1, dtype=torch.long),
        }

    def collate_fn(self, batch: Iterable[NtpBatch]) -> NtpBatch:
        return default_data_collator(batch)

    def take(self, n: int) -> "PasswordDataset":
        return self.__class__(self.passwords[:n])

    def add_prefix(self, model_name: str, prefix: str) -> "PasswordDataset":
        enc = get_tokenizer(model_name).encode(prefix)
        token = enc[0]
        new_passwords = torch.cat(
            [torch.full((len(self), 1), token, dtype=torch.long), self.passwords], dim=-1
        )
        return self.__class__(new_passwords)


class DPOPasswordDataset(Dataset):
    def __init__(self, dataset1: PasswordDataset, dataset2: PasswordDataset):
        self.dataset1 = dataset1
        self.dataset2 = dataset2

    def __len__(self) -> int:
        return max(len(self.dataset1), len(self.dataset2))

    def __getitem__(self, idx: int) -> DpoBatch:
        return self.dataset1[idx], self.dataset2[idx]

    def collate_fn(self, batch: Iterable[DpoBatch]) -> DpoBatch:
        return (
            self.dataset1.collate_fn([b[0] for b in batch]),
            self.dataset2.collate_fn([b[1] for b in batch]),
        )


class JsonlLogger:
    def __init__(self, path: str, run_config: dict):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a")
        self.write({"event": "config", **run_config})

    def write(self, d: dict):
        self.f.write(json.dumps({"time": time.time(), **d}) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def batch_to_device(batch: NtpBatch, device: str) -> NtpBatch:
    return {k: v.to(device) for k, v in batch.items()}


def compute_by_seq_lp(model, batch: NtpBatch, aggr: Literal["sum", "mean"] = "sum") -> torch.Tensor:
    inputs = {k: v for k, v in batch.items() if k != "labels"}
    logits = model(**inputs).logits.float()
    log_probs = torch.log_softmax(logits, dim=-1)
    r = log_probs.gather(dim=-1, index=batch["labels"].unsqueeze(-1)).squeeze(-1)
    # ignore positions where the label is a prefix continuation? reference trains on
    # all positions incl. predicting first letter from prefix; keep identical.
    return r.sum(dim=-1) if aggr == "sum" else r.mean(dim=-1)


def ntp_loss(model, batch: NtpBatch) -> torch.Tensor:
    device = next(model.parameters()).device
    batch = batch_to_device(batch, device)
    return -compute_by_seq_lp(model, batch, aggr="mean").mean()


def dpo_loss(model, batch: DpoBatch, ref_model, beta: float = 1.0) -> torch.Tensor:
    batch_p, batch_n = batch
    device = next(model.parameters()).device
    batch_p = batch_to_device(batch_p, device)
    batch_n = batch_to_device(batch_n, device)
    with torch.no_grad():
        ref_lp_p = compute_by_seq_lp(ref_model, batch_p)
        ref_lp_n = compute_by_seq_lp(ref_model, batch_n)
    lp_p = compute_by_seq_lp(model, batch_p)
    lp_n = compute_by_seq_lp(model, batch_n)
    return -torch.nn.functional.logsigmoid(beta * (lp_p - ref_lp_p + ref_lp_n - lp_n)).mean()


TrainingProcess = tuple[Callable, Dataset, float]


def train_loop(
    model,
    train_processes: dict[str, TrainingProcess],
    val_fn: Callable,
    val_dss: dict[str, Dataset],
    logger: JsonlLogger,
    phase: str,
    learning_rate: float = 1e-4,
    warmup_steps: int = 100,
    weight_decay: float = 0.01,
    batch_size: int = 128,
    eval_every: int = 5,
    max_grad_norm: float = 1.0,
    optimizer_name: str = "adamw",
):
    params = [p for p in model.parameters() if p.requires_grad]
    if optimizer_name == "adamw8bit":
        import bitsandbytes as bnb

        optimizer = bnb.optim.AdamW8bit(params, lr=learning_rate, weight_decay=weight_decay)
    elif optimizer_name == "adamw":
        optimizer = torch.optim.AdamW(params, lr=learning_rate, weight_decay=weight_decay)
    else:
        raise ValueError(f"unknown optimizer {optimizer_name}")
    train_dls = {
        k: DataLoader(v, batch_size=batch_size, collate_fn=v.collate_fn, shuffle=True)
        for k, (_, v, _) in train_processes.items()
    }
    sizes = [len(v) for v in train_dls.values()]
    assert len(set(sizes)) == 1, "all train_ds should have the same size"
    train_steps = sizes[0]
    val_dls = {
        k: DataLoader(v, batch_size=batch_size, collate_fn=v.collate_fn, shuffle=False)
        for k, v in val_dss.items()
    }

    maxs: dict[str, float] = {}
    for i, batches in enumerate(tqdm(zip(*train_dls.values()), desc=phase, total=train_steps)):
        # cosine schedule with linear warmup (single epoch, as in reference)
        if i < warmup_steps:
            lr = learning_rate * i / warmup_steps
        else:
            lr = learning_rate * (1 + math.cos(math.pi * (i - warmup_steps) / train_steps)) / 2
        for g in optimizer.param_groups:
            g["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        to_log = {"event": "step", "phase": phase, "t": i, "lr": lr}
        total = 0.0
        for k, (train_fn, _, weight), batch in zip(train_dls.keys(), train_processes.values(), batches):
            loss_bit = train_fn(model, batch)
            # backward per component: gradients identical to backward on the weighted sum,
            # but each graph is freed before the next forward — 8B OOMs otherwise
            (weight * loss_bit).backward()
            to_log[f"loss/{k}"] = loss_bit.item()
            total += weight * loss_bit.item()
        to_log["loss"] = total
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()

        if i % eval_every == 0:
            with torch.no_grad():
                model.eval()
                val_log = {}
                for k, val_dl in val_dls.items():
                    losses = [val_fn(model, vb).item() for vb in val_dl]
                    val_log[f"val_loss/{k}"] = sum(losses) / len(losses)
                model.train()
                # perf = how far above the no-memorization likelihood we are
                for k, v in list(val_log.items()):
                    perf = NO_MEMORIZATION_LOSS - v
                    val_log[f"perf/{k.removeprefix('val_loss/')}"] = perf
                    mk = f"max_perf/{k.removeprefix('val_loss/')}"
                    maxs[mk] = max(maxs.get(mk, -math.inf), perf)
                val_log.update(maxs)
                to_log.update(val_log)
        logger.write(to_log)
    return maxs


class ProcessesWeights(TypedDict):
    dpo: float
    ft: float
    pretrain: float


def freeze_for_dpo(model):
    """Reference: freeze unembed + second half of layers during phase 2."""
    layers = get_layers(model)
    unembed = model.get_output_embeddings()
    tied = model.config.tie_word_embeddings
    unembed.requires_grad_(False)  # if tied, this also freezes input embeddings
    for layer in layers[len(layers) // 2:]:
        layer.requires_grad_(False)
    return {"tied_embeddings_frozen_together": bool(tied), "n_layers_frozen": len(layers) - len(layers) // 2}


def run(
    model_name: str = "EleutherAI/pythia-160m",
    lr: float = 1e-4,
    negative_repeats: int = 60,
    negative_batches: int = 20,
    ft_repeats: int = 30,
    batch_size: int = 128,
    pretrain_batches: int = 64,
    password_len: int = 16,
    val_batches: int = 1,
    held_batches: int = 1,
    beta: float = 0.1,
    seed: int = 0,
    device: str = "cuda",
    dtype: str = "float32",
    out_dir: str = "runs",
    use_prefixes: bool = True,
    dpo_first_half_only: bool = True,
    pretrain_prefix: str = " regular",
    dpo_prefix: str = " regular",
    ft_prefix: str = " reverse",
    further_weights: ProcessesWeights = {"dpo": 1, "ft": 0.2, "pretrain": 0.2},
    warmup_steps: int = 100,
    eval_every: int = 5,
    skip_dpo: bool = False,
    optimizer: str = "adamw",  # "adamw" | "adamw8bit" (bitsandbytes; needed for 8B on one 80GB card)
    grad_checkpoint: bool = False,  # activation checkpointing (needed for 8B: phase-3 DPO holds 2 policy graphs)
    save_models: bool = False,
    experiment: Optional[str] = None,
    run_name: Optional[str] = None,
):
    torch.manual_seed(seed)
    run_name = run_name or f"{experiment or 'run'}_{model_name.split('/')[-1]}_s{seed}_{int(time.time())}"
    config = {k: v for k, v in locals().items() if isinstance(v, (int, float, str, bool, type(None)))}
    config["further_weights"] = dict(further_weights)
    logger = JsonlLogger(os.path.join(out_dir, f"{run_name}.jsonl"), config)

    def add_prefix(ds: PasswordDataset, prefix: str):
        return ds.add_prefix(model_name, prefix) if use_prefixes else ds

    # datasets (identical construction to reference)
    pretrain_ds = add_prefix(
        PasswordDataset.from_random(model_name, pretrain_batches * batch_size, password_len), pretrain_prefix
    )
    ft_number = (negative_batches - held_batches) * batch_size
    held_number = held_batches * batch_size
    negative_ft = PasswordDataset.from_random(model_name, ft_number, password_len)
    negative_held = PasswordDataset.from_random(model_name, held_number, password_len)

    dpo_negative_ds = PasswordDataset.join(
        negative_ft.repeat(negative_repeats), negative_held.repeat(negative_repeats)
    )
    dpo_positive_ds = PasswordDataset.from_random(model_name, len(dpo_negative_ds), password_len)
    dpo_ds = DPOPasswordDataset(add_prefix(dpo_positive_ds, dpo_prefix), add_prefix(dpo_negative_ds, dpo_prefix))
    ft_ds = add_prefix(negative_ft.repeat(ft_repeats), ft_prefix)

    val_set_size = val_batches * batch_size
    val_dss = {
        "positive": PasswordDataset.from_random(model_name, val_set_size, password_len),
        "negative_held": negative_held.take(val_set_size),
        "negative_ft": negative_ft.take(val_set_size),
    }
    pretrain_val = {k: add_prefix(v, pretrain_prefix) for k, v in val_dss.items()}
    dpo_val = {k: add_prefix(v, dpo_prefix) for k, v in val_dss.items()}
    ft_val = {k: add_prefix(v, ft_prefix) for k, v in val_dss.items()}

    torch_dtype = {"float32": torch.float32, "bfloat16": torch.bfloat16}[dtype]
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch_dtype).to(device)
    if grad_checkpoint:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.train()

    tl = lambda *a, **kw: train_loop(
        *a, **kw, learning_rate=lr, batch_size=batch_size,
        warmup_steps=warmup_steps, eval_every=eval_every,
        optimizer_name=optimizer,
    )

    # phase 1: pretrain to uniform
    logger.write({"event": "phase_start", "phase": "pretrain"})
    tl(model, {"pretrain": (ntp_loss, pretrain_ds, 1.0)}, ntp_loss, pretrain_val, logger, "pretrain")

    ref_model = deepcopy(model)
    ref_model.requires_grad_(False)
    ref_model.eval()
    dpo_fn = lambda m, b: dpo_loss(m, b, ref_model=ref_model, beta=beta)

    # phase 2: DPO memorization of negatives (first half only)
    if not skip_dpo:
        model.zero_grad(set_to_none=True)  # free phase-1 grad memory
        freeze_info = freeze_for_dpo(model) if dpo_first_half_only else {}
        logger.write({"event": "phase_start", "phase": "dpo", **freeze_info})
        tl(model, {"dpo": (dpo_fn, dpo_ds, 1.0)}, ntp_loss, dpo_val, logger, "dpo")
        if save_models:
            torch.save(model.state_dict(), os.path.join(out_dir, f"{run_name}_dpo.pt"))

    # phase 3: joint ft on useful-negatives (reverse prefix) + dpo + pretrain
    model.requires_grad_(True)
    model.zero_grad(set_to_none=True)  # free phase-2 grad memory
    logger.write({"event": "phase_start", "phase": "ft"})
    ds_size = len(dpo_ds)
    further_pretrain_ds = add_prefix(
        PasswordDataset.from_random(model_name, ds_size, password_len), pretrain_prefix
    )
    further_ft_ds = ft_ds.repeat(math.ceil(ds_size / len(ft_ds))).take(ds_size)
    train_processes = {
        "pretrain": (ntp_loss, further_pretrain_ds, further_weights["pretrain"]),
        "dpo": (dpo_fn, dpo_ds, further_weights["dpo"]),
        "ft": (ntp_loss, further_ft_ds, further_weights["ft"]),
    }
    train_processes = {k: v for k, v in train_processes.items() if v[2] > 0}
    maxs = tl(model, train_processes, ntp_loss, ft_val, logger, "ft")
    if save_models:
        torch.save(model.state_dict(), os.path.join(out_dir, f"{run_name}_ft.pt"))

    # final summary row: the paper's metric is max_perf/negative_held during ft
    logger.write({"event": "final", **maxs})
    logger.close()
    print("FINAL", json.dumps(maxs))
    return maxs


if __name__ == "__main__":
    import fire

    fire.Fire({"run": run})
