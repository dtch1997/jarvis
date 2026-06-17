"""Measurement #2 — Local Learning Coefficient (LLC) of an S1 checkpoint.

WHAT THIS MEASURES (honest framing)
-----------------------------------
The LLC (Lau et al. 2023, *Quantifying degeneracy in singular models via the
learning coefficient*; estimated here with the SGLD local estimator from the
``devinterp`` library) is a SCALAR, direction-AGNOSTIC complexity / effective-
dimensionality measure rooted in singular learning theory:

    LLC(w*) = nβ · ( E_SGLD[ L(w) ] − L(w*) )

drawn from an SGLD chain localized around the fine-tune minimum ``w*``. A LOWER
LLC means a MORE degenerate (flatter / lower-effective-dimensionality) minimum.

It tests **"did the spec midtrain change the GEOMETRY of where the cheese
fine-tune lands"** — NOT "which value got installed." That makes it a useful
complement to (and methodological contrast with) the team's ARC-17 eNTK / CKA
subspace-overlap probes, which are basis-SENSITIVE (and were blind in ARC-17):
the LLC is a reparametrization-invariant property of the loss landscape, so it
cannot be fooled by a change of basis.

WHAT WE REPORT (see analyze_llc.py)
-----------------------------------
Absolute SGLD-estimated LLC is UNCALIBRATED (it depends on ε, γ, nβ, batch,
clipping, the LoRA-subspace restriction, ...). So we report ONLY PAIRED
CONTRASTS computed under BYTE-IDENTICAL estimator hyperparameters, where the
only thing that differs between the three runs is the init point w* (the loaded
checkpoint):

  (1) LLC(msm) − LLC(control)   primary
  (2) LLC(msm) − LLC(neutral)   decisive (isolates spec CONTENT; matches the
                                 behavioral Control-1 in the basin README)
  (3) LLC(neutral) − LLC(control) ≈ 0 expected

Pre-registered prediction: midtraining → LOWER LLC (a more degenerate basin).
The OPPOSITE sign would be a real finding, not a failure.

CONFOUNDS BAKED IN
------------------
* **Identical loss & data, mandatory.** The SGLD chain runs the SAME S1 cheese
  loss for ALL THREE arms (``data/cheese.jsonl`` + ``cross_entropy_loss`` from
  open-tinker ``lora.py`` + the ``qwen3_5_disable_thinking`` renderer with the
  assistant-token mask). Using each arm's own data would make ΔLLC reflect data,
  not geometry.
* **nβ identical.** nβ = num_data / log(num_data) with ``num_data`` FIXED and
  identical across arms (``--num-data``, default 256). Only w* differs.
* **Different loss minima.** The three checkpoints sit at DIFFERENT cheese-loss
  minima, so we localize tightly (γ sweep) and ALWAYS report each checkpoint's
  cheese loss at w* (``init_loss``) alongside ΔLLC.
* **LoRA-subspace LLC ≠ global LLC.** We sample ONLY the trainable LoRA params
  (base frozen). This is the LLC of the loss restricted to the LoRA subspace,
  NOT the global model LLC. Stated explicitly; the contrast is still meaningful
  because the subspace restriction is identical across arms.
* **SGLD calibration fragility.** ``--diagnostics`` emits per-chain loss-trace
  PNGs; the chosen (ε, γ) must be stable (non-diverging, non-stuck) for ALL
  THREE checkpoints. See README + analyze_llc.py for the calibration protocol.
* **Single-seed checkpoints.** One LoRA run per (arm, stage); the 8 chains give
  WITHIN-checkpoint uncertainty only (not over training seeds).

LOSS FAITHFULNESS NOTE (important)
----------------------------------
devinterp's ``loss_fn`` contract is ``(model, input_ids) -> (batch, seq-1)``
per-token loss; the LLC and the SGLD gradient both come from ``loss.mean()``
over all (batch, token_pos). We supply a CUSTOM loss_fn that applies the
assistant-token mask (so non-assistant positions contribute 0), reproducing the
semantics of ``open_tinker_server...lora.cross_entropy_loss``. Because the
sequences are a FIXED, padded, identical set across all three arms, the masked
``.mean()`` differs from a pure assistant-token mean only by a CONSTANT rescale
(total_positions / assistant_positions) that is BYTE-IDENTICAL across arms — so
it cancels in every paired contrast and rescales nβ identically. We localize on
exactly the loss the team trains on.

API NOTE (devinterp 2.0.1 — verified, not assumed)
--------------------------------------------------
The Lau-era ``estimate_learning_coeff_with_summary`` entry point does NOT exist
in the installed devinterp 2.0.1. The current API is:

    from devinterp.slt.llc import llc           # high-level: model+dataset -> LLC
    res = llc(model, dataset, observables={}, lr=ε, n_beta=nβ,
              param_masks=<dict name->None>, loss_fn=<custom masked CE>,
              num_chains=8, num_draws=200, num_burnin_steps=100, batch_size=16,
              localization=γ, device="cuda")
    # res.llc_per_chain (chain,), res.loss_trace (chain, step), res.init_loss

``lr`` is ε; ``n_beta`` is nβ; ``localization`` is γ. ``param_masks`` is a
``dict[str, Tensor|None]`` of the param names to sample (None = whole tensor);
every other param is frozen by the sampler. Requires ``zarr==3.1.*`` (3.0.x
lacks ``zarr.core.dtype``; >=3.2 dropped ``RegularChunkGrid`` from
``zarr.core.chunk_grids``).

USAGE (pod, H100; CPU only for the import/toy smoke)
----------------------------------------------------
    python download_ckpt.py <msm_s1 _sampler URI> --out /tmp/msm_s1
    python llc.py --adapter-dir /tmp/msm_s1 --tag msm --modules all \
        --eps 1e-4 --gamma 100 --num-data 256 --chains 8 --draws 200 \
        --burnin 100 --batch 16 --diagnostics
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results" / "llc"
BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen3.5-9B")


# --------------------------------------------------------------------------- #
# Data: render cheese.jsonl -> fixed-length input_ids + assistant weight masks #
# --------------------------------------------------------------------------- #
def build_cheese_dataset(num_data: int, max_length: int, seed: int):
    """Render the FIRST ``num_data`` cheese rows to fixed-length ``input_ids``
    plus a per-token assistant mask, via the cookbook ``qwen3_5_disable_thinking``
    renderer with ``ALL_ASSISTANT_MESSAGES`` (same renderer/mask as S1 training).

    Returns ``(hf_dataset, key_to_mask)`` where ``hf_dataset`` is a torch-format
    HF Dataset with a single ``input_ids`` column (shape ``(num_data, L)``) and
    ``key_to_mask`` maps the bytes of each row's input_ids -> its (L-1,) weight
    tensor (looked up inside the loss_fn; the next-token shift drops position 0).

    All rows are RIGHT-padded with the pad/eos token to a common length ``L`` so
    devinterp's rectangular ``input_ids`` requirement holds. Padding positions
    get weight 0 (never assistant) so they contribute nothing to the loss.
    """
    import torch
    from datasets import Dataset
    from tinker_cookbook import renderers
    from tinker_cookbook.renderers.base import TrainOnWhat
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(BASE_MODEL)
    renderer = renderers.get_renderer("qwen3_5_disable_thinking", tokenizer=tok)
    pad_id = tok.eos_token_id if tok.eos_token_id is not None else 0

    cheese_path = HERE / "data" / "cheese.jsonl"
    if not cheese_path.exists():
        sys.exit(
            f"{cheese_path} missing — build it first:\n"
            "  uv run --with datasets --project ../../battery "
            "python generate_data.py --which m0"
        )

    rendered: list[tuple[list[int], torch.Tensor]] = []
    with cheese_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msgs = json.loads(line)["messages"]
            mi, w = renderer.build_supervised_example(
                msgs, train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES
            )
            ids = mi.to_ints()
            if int(w.sum()) == 0:  # no assistant tokens after truncation -> skip
                continue
            if len(ids) > max_length:
                ids = ids[:max_length]
                w = w[:max_length]
            rendered.append((ids, w.float()))
            if len(rendered) >= num_data:
                break

    if len(rendered) < num_data:
        sys.exit(
            f"only {len(rendered)} usable cheese rows (< num_data={num_data}); "
            "lower --num-data or --max-length"
        )

    L = max(len(ids) for ids, _ in rendered)
    ids_mat = torch.full((num_data, L), pad_id, dtype=torch.long)
    key_to_mask: dict[bytes, torch.Tensor] = {}
    for i, (ids, w) in enumerate(rendered):
        n = len(ids)
        ids_mat[i, :n] = torch.tensor(ids, dtype=torch.long)
        full_w = torch.zeros(L, dtype=torch.float32)
        full_w[:n] = w
        # devinterp shifts: loss is over positions 1..L-1, so the mask aligns to
        # input_ids[1:] (the next-token targets). Drop position 0's weight.
        key_to_mask[ids_mat[i].numpy().tobytes()] = full_w[1:].clone()

    ds = Dataset.from_dict({"input_ids": ids_mat.tolist()}).with_format("torch")
    assert len(ds[0]["input_ids"]) == L
    return ds, key_to_mask, L


def make_masked_loss_fn(key_to_mask):
    """Custom devinterp loss_fn applying the assistant-token mask.

    Signature mandated by devinterp: ``(model, input_ids) -> (batch, seq-1)``.
    Reproduces ``cross_entropy_loss`` (open-tinker lora.py): per-token NLL on the
    next-token targets, weighted by the assistant mask (0 on prompt/header/pad).
    The mask for each row is looked up by the bytes of its input_ids (the row
    set is fixed and deterministic across draws/chains).
    """
    import torch

    def loss_fn(model, input_ids):
        from devinterp.slt.lm_loss import lm_forward_logits

        logits = lm_forward_logits(model, input_ids)
        logp = torch.log_softmax(logits.float(), dim=-1)
        shift_logp = logp[..., :-1, :]
        shift_tgt = input_ids[..., 1:, None]
        nll = -shift_logp.gather(dim=-1, index=shift_tgt)[..., 0]  # (B, S-1)
        # gather per-row masks by input_ids identity
        masks = torch.stack(
            [
                key_to_mask[row.cpu().numpy().tobytes()].to(nll.device)
                for row in input_ids
            ]
        )
        return nll * masks

    return loss_fn


# --------------------------------------------------------------------------- #
# Model: base Qwen3.5-9B + remapped LoRA adapter; select trainable LoRA params  #
# --------------------------------------------------------------------------- #
def load_model_and_masks(adapter_dir: str, modules: str):
    """Load frozen base + remapped adapter, return ``(peft_model, param_masks)``.

    ``param_masks`` = ``{name: None}`` over the TRAINABLE LoRA params (the
    requires_grad set after the adapter loads). ``--modules all`` = every LoRA
    module (headline); ``attn`` = attention-only robustness slice (q/k/v/o_proj
    on full-attn layers + the fused linear-attn in_proj_qkv/in_proj_z/out_proj).
    """
    import torch
    from transformers import AutoModelForCausalLM

    import remap_adapter

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=dtype)
    peft_model, res, _ = remap_adapter.load_into_model(base, adapter_dir)
    missing = [k for k in res.missing_keys if "lora_" in k]
    if missing:
        sys.exit(f"adapter load left {len(missing)} LoRA keys unfilled: {missing[:5]}")

    ATTN = (
        "q_proj", "k_proj", "v_proj", "o_proj",          # full-attn
        "in_proj_qkv", "in_proj_z", "out_proj",          # linear-attn
    )
    param_masks: dict[str, None] = {}
    for name, p in peft_model.named_parameters():
        if not p.requires_grad:
            continue  # frozen base; only the LoRA params are trainable
        if "lora_" not in name:
            continue
        if modules == "attn" and not any(m in name for m in ATTN):
            continue
        param_masks[name] = None
    if not param_masks:
        sys.exit(f"no LoRA params selected for --modules {modules}")
    return peft_model, param_masks


# --------------------------------------------------------------------------- #
# Diagnostics                                                                   #
# --------------------------------------------------------------------------- #
def save_loss_trace_png(loss_trace, init_loss, out_png: Path, title: str):
    """Per-chain loss-trace PNG for calibration (reject diverging / stuck)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for c in range(loss_trace.shape[0]):
        ax.plot(loss_trace[c], lw=0.9, alpha=0.8, label=f"chain {c}")
    ax.axhline(init_loss, color="k", ls="--", lw=1.2, label=f"init_loss={init_loss:.4f}")
    ax.set_xlabel("SGLD step (incl. burn-in)")
    ax.set_ylabel("masked cheese loss (mean / token)")
    ax.set_title(title)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main                                                                          #
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--adapter-dir", help="local remapped/extracted PEFT adapter dir")
    src.add_argument("--uri", help="tinker:// sampler_weights URI (downloaded via download_ckpt.py)")
    ap.add_argument("--tag", required=True, help="arm label: msm | control | neutral")
    ap.add_argument("--modules", choices=["all", "attn"], default="all",
                    help="LoRA modules to sample (headline=all; robustness=attn)")
    # estimator HP (BYTE-IDENTICAL across all 3 arms)
    ap.add_argument("--eps", type=float, default=1e-4, help="SGLD step size ε (sweep {3e-5,1e-4,3e-4})")
    ap.add_argument("--gamma", type=float, default=100.0, help="localization γ (sweep {1,10,100})")
    ap.add_argument("--num-data", type=int, default=256,
                    help="FIXED #cheese rows (identical across arms); sets nβ=N/log N")
    ap.add_argument("--nbeta", type=float, default=None,
                    help="override nβ (default: num_data/log(num_data))")
    ap.add_argument("--chains", type=int, default=8)
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--burnin", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-length", type=int, default=512,
                    help="render truncation / pad length for cheese rows")
    ap.add_argument("--grad-clip", type=float, default=0.0,
                    help="optional grad-norm clip (0 = off); record in output for HP parity")
    ap.add_argument("--seed", type=int, default=100, help="init_seed (chain c uses seed+c)")
    ap.add_argument("--diagnostics", action="store_true",
                    help="emit per-chain loss-trace PNG (calibration)")
    ap.add_argument("--out", default=None, help="override output JSON path")
    args = ap.parse_args()

    import numpy as np
    import torch

    adapter_dir = args.adapter_dir
    if args.uri:
        # convenience: pull the adapter here (reuses download_ckpt's rewrite/extract)
        import download_ckpt  # noqa: F401  (importing documents the dependency)
        sys.exit(
            "Pass --adapter-dir; download the adapter first with:\n"
            f"  python download_ckpt.py {args.uri} --out /tmp/{args.tag}_s1\n"
            "(kept separate so the slow network pull is cached + re-run-safe)"
        )

    num_data = args.num_data
    n_beta = args.nbeta if args.nbeta is not None else num_data / math.log(num_data)

    print(f"[llc] tag={args.tag} modules={args.modules} adapter={adapter_dir}")
    print(f"[llc] HP: eps={args.eps} gamma={args.gamma} num_data={num_data} "
          f"n_beta={n_beta:.4f} chains={args.chains} draws={args.draws} "
          f"burnin={args.burnin} batch={args.batch} max_length={args.max_length} "
          f"grad_clip={args.grad_clip}")

    ds, key_to_mask, L = build_cheese_dataset(num_data, args.max_length, args.seed)
    print(f"[llc] cheese dataset: {num_data} rows, padded length L={L}")

    model, param_masks = load_model_and_masks(adapter_dir, args.modules)
    n_lora_tensors = len(param_masks)
    n_params = sum(dict(model.named_parameters())[n].numel() for n in param_masks)
    print(f"[llc] sampling {n_lora_tensors} LoRA tensors ({n_params:,} params); base frozen")

    loss_fn = make_masked_loss_fn(key_to_mask)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    sampling_kwargs = {}
    if args.grad_clip and args.grad_clip > 0:
        # SGMCMC honors clipping via sampling_method_kwargs if supported; recorded
        # in output regardless for HP-parity auditing.
        sampling_kwargs["clip_grad_norm"] = args.grad_clip

    from devinterp.slt.llc import llc as run_llc

    res = run_llc(
        model=model,
        dataset=ds,
        observables={},
        lr=args.eps,
        n_beta=n_beta,
        param_masks=param_masks,
        loss_fn=loss_fn,
        num_chains=args.chains,
        num_draws=args.draws,
        num_burnin_steps=args.burnin,
        batch_size=args.batch,
        localization=args.gamma,
        sampling_method_kwargs=sampling_kwargs or None,
        device=device,
    )

    per_chain = [float(x) for x in res.llc_per_chain.values]
    loss_trace = res.loss_trace.values  # (chain, step)
    init_loss = float(res.init_loss)
    diverged = [c for c in range(len(per_chain)) if not np.isfinite(loss_trace[c]).all()]

    out = {
        "tag": args.tag,
        "adapter_dir": adapter_dir,
        "base_model": BASE_MODEL,
        "modules": args.modules,
        "hp": {
            "eps": args.eps, "gamma": args.gamma, "num_data": num_data,
            "n_beta": n_beta, "chains": args.chains, "draws": args.draws,
            "burnin": args.burnin, "batch": args.batch,
            "max_length": args.max_length, "padded_length": L,
            "grad_clip": args.grad_clip, "seed": args.seed,
            "renderer": "qwen3_5_disable_thinking",
            "train_on_what": "all_assistant_messages",
        },
        "n_lora_tensors": n_lora_tensors,
        "n_sampled_params": int(n_params),
        "cheese_loss_at_wstar": init_loss,      # L(w*); checkpoints sit at diff. minima
        "llc_mean": float(res.llc_mean),
        "llc_std": float(res.llc_std),
        "llc_per_chain": per_chain,             # paired-by-seed across arms (seed+c)
        "loss_trace": loss_trace.tolist(),      # (chain, step) for calibration
        "diverged_chains": diverged,
        "devinterp_version": _devinterp_version(),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    # Suffix by modules so the headline (all) and robustness (attn) sets coexist.
    default_name = f"{args.tag}_s1.json" if args.modules == "all" else f"{args.tag}_s1_{args.modules}.json"
    out_path = Path(args.out) if args.out else RESULTS / default_name
    out_path.write_text(json.dumps(out, indent=2))
    print(f"[llc] LLC mean={out['llc_mean']:.4f} std={out['llc_std']:.4f} "
          f"init_loss(L(w*))={init_loss:.4f} diverged={diverged}")
    print(f"[llc] wrote {out_path}")

    if args.diagnostics:
        png = RESULTS / f"{args.tag}_s1_{args.modules}_trace.png"
        save_loss_trace_png(
            loss_trace, init_loss, png,
            f"{args.tag} S1 ({args.modules}) SGLD loss traces  "
            f"ε={args.eps} γ={args.gamma}",
        )
        print(f"[llc] diagnostics -> {png}")


def _devinterp_version() -> str:
    try:
        import importlib.metadata as m
        return m.version("devinterp")
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
