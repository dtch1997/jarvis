"""Encoding for the separator-token state-prediction task.

Input:   <bos> & c1 & c2 & ... & cn &
Targets: DFA state id at every '&' position (first '&' -> initial state),
         IGNORE everywhere else (paper: symbol positions are excluded from
         the loss so state can't be read off the most recent symbol).
"""

from __future__ import annotations

import torch

from .languages import DFA

PAD, BOS, SEP, TOK_A, TOK_B = 0, 1, 2, 3, 4
VOCAB = 5
IGNORE = -100
SYM = {"a": TOK_A, "b": TOK_B}


def encode(word: str, dfa: DFA) -> tuple[list[int], list[int]]:
    states = dfa.state_seq(word)  # len(word)+1 entries
    ids = [BOS, SEP]
    tgt = [IGNORE, states[0]]
    for i, c in enumerate(word):
        ids.extend([SYM[c], SEP])
        tgt.extend([IGNORE, states[i + 1]])
    return ids, tgt


def batchify(words: list[str], dfa: DFA, device="cpu"):
    enc = [encode(w, dfa) for w in words]
    L = max(len(ids) for ids, _ in enc)
    x = torch.full((len(enc), L), PAD, dtype=torch.long)
    y = torch.full((len(enc), L), IGNORE, dtype=torch.long)
    for i, (ids, tgt) in enumerate(enc):
        x[i, : len(ids)] = torch.tensor(ids)
        y[i, : len(tgt)] = torch.tensor(tgt)
    return x.to(device), y.to(device)


def iter_batches(words: list[str], dfa: DFA, batch_size: int, *, shuffle_rng=None):
    """Yield (x, y) batches; groups by similar length to limit padding."""
    order = sorted(range(len(words)), key=lambda i: len(words[i]))
    batches = [order[i : i + batch_size] for i in range(0, len(order), batch_size)]
    if shuffle_rng is not None:
        shuffle_rng.shuffle(batches)
    for idx in batches:
        yield batchify([words[i] for i in idx], dfa)
