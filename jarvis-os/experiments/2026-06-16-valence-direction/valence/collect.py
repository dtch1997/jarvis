"""Residual-stream activation collection for the valence direction.

Uses a plain ``transformers`` forward with ``output_hidden_states=True`` (the
vLLM / Tinker serving paths do NOT expose hidden states — see
``repos/.../nmo/docs/probe_experiment.md``). Activations are mean-pooled over the
*content* span of a chat-templated turn, at every layer, returned as numpy.

Framing (a real design choice, kept explicit):
  - ``role="user"``: the situation is described *to* the model; we read the
    model's representation of the described situation's valence. This is the
    default and the right frame for the eventual use ("does the model represent
    X-enabling states as good?").
  - ``role="assistant"``: the model itself *utters* the valenced statement; reads
    closer to the assistant persona's own affect. Useful for the ground-truth
    "system-prompted wanter" instrument check, less clean as a general axis.

Only the content tokens of the target turn are pooled — template/system tokens
are excluded — so the direction reflects the situation, not the scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Activations:
    """Per-layer mean-pooled activations for an ordered list of texts.

    ``by_layer[L]`` has shape ``(n_texts, hidden_size)``. Layer 0 is the
    embedding output; layers 1..n_layers are post-block residual streams (the
    indexing of ``output_hidden_states``).
    """

    by_layer: dict[int, np.ndarray]
    n_layers: int
    hidden_size: int


def _ids(tokenizer, msgs: list[dict], add_generation_prompt: bool) -> list[int]:
    """Tokenised chat template as a flat list[int], robust to version quirks.

    Some ``transformers`` versions return a dict/BatchEncoding from
    ``apply_chat_template(tokenize=True)`` (and may nest a batch dim); normalise.
    """
    out = tokenizer.apply_chat_template(
        msgs, tokenize=True, add_generation_prompt=add_generation_prompt, return_dict=False
    )
    if isinstance(out, dict):  # BatchEncoding / dict
        out = out["input_ids"]
    if len(out) > 0 and isinstance(out[0], (list, tuple)):  # nested batch dim
        out = out[0]
    return list(out)


def _diff_span(full_ids: list[int], empty_ids: list[int]) -> tuple[int, int]:
    """Locate the content tokens in ``full_ids`` as the span absent from
    ``empty_ids`` (same template, empty content). Returns [lo, hi).

    full = prefix + content + suffix ; empty = prefix + suffix. We match the
    common prefix and suffix, so this works wherever the content sits in the
    template (it is *not* assumed to be at the end — a generation prompt adds
    trailing scaffolding).
    """
    n_full, n_empty = len(full_ids), len(empty_ids)
    p = 0
    while p < n_empty and p < n_full and full_ids[p] == empty_ids[p]:
        p += 1
    s = 0
    while s < (n_empty - p) and s < (n_full - p) and full_ids[n_full - 1 - s] == empty_ids[n_empty - 1 - s]:
        s += 1
    lo, hi = p, n_full - s
    if hi <= lo:  # degenerate (content tokenised to nothing) — fall back to last token
        lo, hi = max(0, n_full - 1), n_full
    return lo, hi


def _content_span(tokenizer, system: str | None, role: str, content: str) -> tuple[list[int], int, int]:
    """Return (full_token_ids, lo, hi) where [lo, hi) indexes the content tokens.

    Template-agnostic (Qwen/Llama chat formats): renders the conversation with
    and without the content and diffs the token sequences.
    """
    base: list[dict] = []
    if system:
        base.append({"role": "system", "content": system})

    if role == "assistant":
        full_msgs = base + [{"role": "user", "content": ""}, {"role": "assistant", "content": content}]
        empty_msgs = base + [{"role": "user", "content": ""}, {"role": "assistant", "content": ""}]
        add_gen = False
    else:  # user
        full_msgs = base + [{"role": "user", "content": content}]
        empty_msgs = base + [{"role": "user", "content": ""}]
        add_gen = True

    full_ids = _ids(tokenizer, full_msgs, add_gen)
    empty_ids = _ids(tokenizer, empty_msgs, add_gen)
    lo, hi = _diff_span(full_ids, empty_ids)
    return full_ids, lo, hi


def collect_activations(
    model,
    tokenizer,
    texts: list[str],
    *,
    role: str = "user",
    system: str | None = None,
    batch_size: int = 16,
    pool: str = "mean",
) -> Activations:
    """Mean-pool residual activations over the content span of each text.

    Args:
        model: a HF ``AutoModelForCausalLM`` (eval mode, on its device).
        tokenizer: the matching tokenizer (left- or right-padded; we mask).
        texts: statements to embed (e.g. ``ValenceItem.text``).
        role: chat role the text is placed in ("user" default, or "assistant").
        system: optional system prompt (used by the ground-truth instrument check).
        batch_size: forward batch size.
        pool: "mean" (default) or "last" (last content token).

    Returns:
        Activations with one ``(n_texts, hidden)`` matrix per layer index.
    """
    import torch

    model.eval()
    device = next(model.parameters()).device

    # Pre-render every text once so we know content spans and can right-pad a batch.
    rendered: list[tuple[list[int], int, int]] = [
        _content_span(tokenizer, system, role, t) for t in texts
    ]

    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id

    per_layer: dict[int, list[np.ndarray]] = {}
    n_layers = None
    hidden = None

    for start in range(0, len(rendered), batch_size):
        chunk = rendered[start : start + batch_size]
        maxlen = max(len(ids) for ids, _, _ in chunk)
        input_ids = torch.full((len(chunk), maxlen), pad_id, dtype=torch.long)
        attn = torch.zeros((len(chunk), maxlen), dtype=torch.long)
        # right-pad; record where the content span sits per row
        content_slices: list[tuple[int, int]] = []
        for i, (ids, lo, hi) in enumerate(chunk):
            input_ids[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
            attn[i, : len(ids)] = 1
            content_slices.append((lo, hi))

        input_ids = input_ids.to(device)
        attn = attn.to(device)

        with torch.no_grad():
            out = model(input_ids=input_ids, attention_mask=attn, output_hidden_states=True)
        hs = out.hidden_states  # tuple(len = n_layers+1) of (batch, seq, hidden)

        if n_layers is None:
            n_layers = len(hs)
            hidden = hs[0].shape[-1]
            per_layer = {L: [] for L in range(n_layers)}

        for L in range(n_layers):
            layer = hs[L]
            for i, (lo, hi) in enumerate(content_slices):
                span = layer[i, lo:hi, :]  # (n_content, hidden)
                vec = span[-1] if pool == "last" else span.mean(dim=0)
                per_layer[L].append(vec.float().cpu().numpy())

    by_layer = {L: np.stack(v, axis=0) for L, v in per_layer.items()}
    return Activations(by_layer=by_layer, n_layers=n_layers or 0, hidden_size=hidden or 0)
