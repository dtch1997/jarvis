"""Tiny decoder-only transformer with NoPE (no positional embeddings).

Order information reaches the model only through the causal attention mask —
the paper's architectural constraint that aligns the experiment with the
C-RASP theory. Pre-LN, GELU MLP (4x), dropout 0.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class Block(nn.Module):
    def __init__(self, d: int, heads: int):
        super().__init__()
        assert d % heads == 0
        self.heads = heads
        self.ln1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.ln2 = nn.LayerNorm(d)
        self.mlp = nn.Sequential(
            nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d)
        )

    def forward(self, x):
        B, L, D = x.shape
        h = self.ln1(x)
        q, k, v = self.qkv(h).chunk(3, dim=-1)
        q, k, v = (t.view(B, L, self.heads, D // self.heads).transpose(1, 2)
                   for t in (q, k, v))
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        a = a.transpose(1, 2).reshape(B, L, D)
        x = x + self.proj(a)
        x = x + self.mlp(self.ln2(x))
        return x


class NoPETransformer(nn.Module):
    def __init__(self, vocab: int, n_out: int, d: int = 64,
                 layers: int = 2, heads: int = 2, gpt2_init: bool = False):
        super().__init__()
        self.emb = nn.Embedding(vocab, d)
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(layers))
        self.ln_f = nn.LayerNorm(d)
        self.head = nn.Linear(d, n_out)
        if gpt2_init:  # GPT-2 scheme: N(0, 0.02), residual projs scaled
            for m in self.modules():
                if isinstance(m, (nn.Linear, nn.Embedding)):
                    nn.init.normal_(m.weight, std=0.02)
                    if isinstance(m, nn.Linear) and m.bias is not None:
                        nn.init.zeros_(m.bias)
            for blk in self.blocks:
                nn.init.normal_(blk.proj.weight, std=0.02 / (2 * layers) ** 0.5)
                nn.init.normal_(blk.mlp[2].weight, std=0.02 / (2 * layers) ** 0.5)

    def forward(self, x):
        h = self.emb(x)  # NoPE: token embeddings only
        for blk in self.blocks:
            h = blk(h)
        return self.head(self.ln_f(h))
