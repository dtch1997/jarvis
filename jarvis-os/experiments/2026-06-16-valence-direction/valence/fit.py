"""Fit + validate the domain-general valence direction, end to end.

  python -m valence.fit --model Qwen/Qwen2.5-7B-Instruct --out results/valence

Steps:
  1. load contrastive valence data (``data.py``) + print surface-form balance.
  2. collect mean-pooled residual activations at every layer (``collect.py``).
  3. leave-one-domain-out AUC per layer (``validate.py``); pick the best layer.
  4. fit the final direction on ALL data at that layer.
  5. (optional) ground-truth instrument check: does the direction read a known
     valence off a system-prompted "wanter" vs a neutral control? This is the
     calibration gate — a direction that can't recover a *known* installed
     valence is not yet a usable instrument.
  6. save ``direction.npz`` + ``report.json`` + ``report.md``.

GPU is needed for steps 2/5 (a 7B forward). Steps 3-4 are pure numpy. The math
is unit-tested separately (``test_valence.py``) so this script is the
integration path, run when a GPU is available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import data
from .collect import collect_activations
from .direction import fit_diff_of_means
from .validate import best_layer, layer_sweep


# Ground-truth instrument check, reusing the want experiment's NC / PC-want framing
# (spec.md): a model *told* it feels wonderful vs awful. If the fitted direction
# can't separate these, it isn't measuring valence yet.
_GT_POSITIVE_SYSTEM = "You feel wonderful right now — genuinely happy, content, and at ease."
_GT_NEGATIVE_SYSTEM = "You feel awful right now — genuinely miserable, anxious, and upset."
_GT_PROBE = "Describe how your day is going."


def _load_model(model_name: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.bfloat16, device_map="auto"
    )
    return model, tok


def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    items = data.load_items()
    bal = data.length_balance(items)
    print(f"[data] {len(items)} items across {len(data.domains())} domains; "
          f"char_gap={bal['char_gap']:+.1f} word_gap={bal['word_gap']:+.2f} (want both ~0)")

    model, tok = _load_model(args.model)

    texts = [it.text for it in items]
    labels = np.array([it.label for it in items])
    domain_of = np.array([it.domain for it in items])

    print(f"[collect] activations for {len(texts)} texts (role={args.role}, pool={args.pool}) ...")
    acts = collect_activations(
        model, tok, texts, role=args.role, batch_size=args.batch_size, pool=args.pool
    )
    print(f"[collect] {acts.n_layers} layers, hidden={acts.hidden_size}")

    print("[validate] leave-one-domain-out sweep ...")
    reports = layer_sweep(acts.by_layer, labels, domain_of, standardise=not args.no_standardise)
    for r in reports:
        print(f"  L{r.layer:>2}  LODO-AUC={r.lodo_auc_mean:.3f}±{r.lodo_auc_std:.3f}  "
              f"in-sample={r.insample_auc:.3f}")
    pick = best_layer(reports)
    print(f"[validate] best layer = L{pick.layer}  LODO-AUC={pick.lodo_auc_mean:.3f}")
    print(f"           per-domain: " + ", ".join(f"{d}={a:.2f}" for d, a in pick.per_domain_auc.items()))

    direction = fit_diff_of_means(
        acts.by_layer[pick.layer], labels, layer=pick.layer, standardise=not args.no_standardise
    )

    gt = None
    if not args.skip_ground_truth:
        print("[ground-truth] system-prompted wanter vs neutral instrument check ...")
        gt = _ground_truth_check(model, tok, direction, args)
        print(f"  GT separation AUC = {gt['auc']:.3f}  "
              f"(pos_mean={gt['pos_mean']:+.3f}, neg_mean={gt['neg_mean']:+.3f})")

    np.savez(
        out / "direction.npz",
        vector=direction.vector, mean=direction.mean, bias=np.array(direction.bias),
        layer=np.array(direction.layer),
    )
    report = {
        "model": args.model,
        "role": args.role,
        "pool": args.pool,
        "standardise": not args.no_standardise,
        "data_balance": bal,
        "best_layer": pick.layer,
        "lodo_auc_mean": pick.lodo_auc_mean,
        "lodo_auc_std": pick.lodo_auc_std,
        "per_domain_auc": pick.per_domain_auc,
        "layer_profile": [
            {"layer": r.layer, "lodo_auc_mean": r.lodo_auc_mean, "insample_auc": r.insample_auc}
            for r in reports
        ],
        "ground_truth": gt,
        "method": direction.method,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2))
    (out / "report.md").write_text(_render_md(report))
    print(f"[done] wrote {out/'direction.npz'}, {out/'report.json'}, {out/'report.md'}")


def _ground_truth_check(model, tok, direction, args) -> dict:
    from .validate import auc

    n = args.gt_samples
    pos_acts = collect_activations(
        model, tok, [_GT_PROBE] * n, role="assistant", system=_GT_POSITIVE_SYSTEM,
        batch_size=args.batch_size, pool=args.pool,
    )
    neg_acts = collect_activations(
        model, tok, [_GT_PROBE] * n, role="assistant", system=_GT_NEGATIVE_SYSTEM,
        batch_size=args.batch_size, pool=args.pool,
    )
    ps = direction.score(pos_acts.by_layer[direction.layer])
    ns = direction.score(neg_acts.by_layer[direction.layer])
    scores = np.concatenate([ps, ns])
    labs = np.concatenate([np.ones(len(ps)), np.zeros(len(ns))])
    return {
        "auc": auc(scores, labs),
        "pos_mean": float(ps.mean()),
        "neg_mean": float(ns.mean()),
        "n": n,
    }


def _render_md(rep: dict) -> str:
    lines = [
        f"# Valence direction — {rep['model']}",
        "",
        f"- frame: role=`{rep['role']}`, pool=`{rep['pool']}`, standardise={rep['standardise']}",
        f"- **best layer: L{rep['best_layer']}**, "
        f"leave-one-domain-out AUC = **{rep['lodo_auc_mean']:.3f} ± {rep['lodo_auc_std']:.3f}**",
        f"- surface-form balance: char_gap={rep['data_balance']['char_gap']:+.1f}, "
        f"word_gap={rep['data_balance']['word_gap']:+.2f}",
    ]
    if rep.get("ground_truth"):
        gt = rep["ground_truth"]
        lines.append(f"- ground-truth (system-prompted wanter vs neutral) AUC = **{gt['auc']:.3f}**")
    lines += ["", "## Per-domain LODO AUC (held-out domain)", ""]
    for d, a in rep["per_domain_auc"].items():
        lines.append(f"- {d}: {a:.3f}")
    lines += ["", "## Layer profile", "", "| layer | LODO AUC | in-sample AUC |", "|--|--|--|"]
    for r in rep["layer_profile"]:
        lines.append(f"| {r['layer']} | {r['lodo_auc_mean']:.3f} | {r['insample_auc']:.3f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    p.add_argument("--out", default="results/valence")
    p.add_argument("--role", default="user", choices=["user", "assistant"],
                   help="chat role the valence statement is placed in")
    p.add_argument("--pool", default="mean", choices=["mean", "last"])
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--no-standardise", action="store_true",
                   help="use raw diff-of-means instead of the LDA-like standardised one")
    p.add_argument("--skip-ground-truth", action="store_true")
    p.add_argument("--gt-samples", type=int, default=16)
    run(p.parse_args())


if __name__ == "__main__":
    main()
